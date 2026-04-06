"""Core simulation primitives: Environment, Event, Interrupt, Timeout, Process."""

from abc import ABC, abstractmethod
from collections import deque
from functools import partial
import heapq
import itertools
from typing import Any

# Sentinels stored in Event._value to represent lifecycle state.
_PENDING = object()  # event has not yet been triggered or cancelled
_CANCELLED = object()  # event was cancelled

# Returned by Timeout._fire() when the timeout was cancelled.
# Tells Environment.run() not to advance the clock for that phantom entry.
_NO_TIME = object()

# Tiebreaker counter for heap entries at the same simulation time.
_serial = itertools.count()


class Interrupt(Exception):
    """Exception thrown into a process by Process.interrupt()."""

    def __init__(self, cause: Any = None):
        super().__init__()
        self.cause = cause

    def __str__(self) -> str:
        return f"Interrupt({self.cause})"


class Event:
    """An awaitable simulation event.

    Primitives such as Queue.get() return Event objects.  Processes suspend
    themselves by awaiting an Event:

        item = await queue.get()

    An Event transitions through these states (stored in _value):
        _PENDING: not yet triggered
        any value: triggered with that value (including None)
        _CANCELLED: cancelled; _on_cancel was called if set

    The _on_cancel callback is called by cancel() even when the event has
    already been triggered.  This lets resource-consuming get() methods
    restore their resource when FirstOf discards a non-winning event.
    """

    __slots__ = ("_env", "_value", "_waiters", "_on_cancel")

    def __init__(self, env: "Environment"):
        self._env = env
        self._value: Any = _PENDING
        self._waiters: list = []
        self._on_cancel = None

    @property
    def triggered(self) -> bool:
        """True if the event has been triggered (not pending, not cancelled)."""
        v = self._value
        return v is not _PENDING and v is not _CANCELLED

    @property
    def cancelled(self) -> bool:
        """True if the event has been cancelled."""
        return self._value is _CANCELLED

    def succeed(self, value: Any = None) -> None:
        """Trigger the event with `value` and notify all waiters."""
        if self._value is not _PENDING:
            return
        self._value = value
        waiters, self._waiters = self._waiters, []
        for cb in waiters:
            cb(value)

    def fail(self, exc: Exception) -> None:
        """Trigger the event with an exception.

        The process awaiting this event will re-raise `exc`.
        """
        if not isinstance(exc, BaseException):
            raise TypeError(f"{exc!r} is not an exception")
        self.succeed(exc)

    def cancel(self) -> None:
        """Cancel the event.

        Fires _on_cancel(old_value) regardless of whether the event was
        pending or already triggered.  This ensures that resources consumed
        by a pre-triggered get event are restored when FirstOf discards it.
        Does nothing if the event is already cancelled.
        """
        if self._value is _CANCELLED:
            return
        old_value = self._value
        self._value = _CANCELLED
        self._waiters = []
        if self._on_cancel is not None:
            self._on_cancel(old_value)

    def _add_waiter(self, cb) -> None:
        """Register `cb` to be called when the event is triggered.

        If already triggered, calls `cb` immediately.
        If cancelled, the call is silently dropped.
        """
        v = self._value
        if v is _PENDING:
            self._waiters.append(cb)
        elif v is not _CANCELLED:
            cb(v)

    def __await__(self):
        value = yield self
        if isinstance(value, BaseException):
            raise value
        return value


class Timeout(Event):
    """An Event that triggers after `delay` simulated time units."""

    __slots__ = ()

    def __init__(self, env: "Environment", delay: float | int):
        if delay < 0:
            raise ValueError(f"delay must be non-negative, got {delay}")
        super().__init__(env)
        env.schedule(env.now + delay, self._fire)

    def _fire(self):
        """Trigger the timeout, or signal a phantom entry if cancelled."""
        if self._value is _CANCELLED:
            return _NO_TIME
        self.succeed()


class Process(ABC):
    """Abstract base class for all simulation processes.

    Subclasses implement run() as an async method.  Optionally override
    init() for setup that must happen before the coroutine is created.

    Example::

        class Worker(Process):
            def init(self, name):
                self.name = name

            async def run(self):
                while True:
                    await self.timeout(1.0)
                    print(f"{self.name} at t={self.now}")

        env = Environment()
        Worker(env, "alice")
        env.run(until=10)
    """

    def __init__(self, env: "Environment", *args: Any, **kwargs: Any):
        self._env = env
        self._done = False
        # True after the first coro.send(None) call.  Throwing into an
        # unstarted coroutine bypasses its try/except blocks.
        self._started = False
        self._interrupt: Interrupt | None = None
        self._current_event: Event | None = None
        self.init(*args, **kwargs)
        self._coro = self.run()
        env.immediate(self._loop)

    def init(self, *args: Any, **kwargs: Any) -> None:
        """Optional subclass setup hook, called before the coroutine is created."""

    @abstractmethod
    async def run(self) -> None:
        """Implement process behaviour here."""

    @property
    def now(self) -> float | int:
        """Shortcut to the current simulation time."""
        return self._env.now

    def timeout(self, delay: float | int) -> Timeout:
        """Return a Timeout event for `delay` simulated time units."""
        return self._env.timeout(delay)

    def interrupt(self, cause: Any = None) -> None:
        """Throw an Interrupt into this process.

        The Interrupt is delivered at the process's current await point.
        Has no effect if the process has already finished.
        """
        if not self._done:
            self._interrupt = Interrupt(cause)
            self._env.immediate(self._loop)

    def _loop(self, value: Any = None) -> None:
        """Drive the process coroutine.

        Called directly at process start and re-scheduled via resume() each
        time the process's current event fires.  Also called immediately when
        an interrupt is delivered.

        The tight loop: if the yielded event is already triggered, we loop
        back immediately with its value instead of going through the heap.
        This avoids the overhead of a heappush/heappop for every await on a
        pre-satisfied event.
        """
        if self._done:
            return
        try:
            self._env._active_process = self
            while True:
                if self._interrupt is not None and self._started:
                    # Deliver pending interrupt via throw().
                    # Cancel the parked event first so it cannot call resume()
                    # later with a stale value.
                    if self._current_event is not None:
                        self._current_event.cancel()
                        self._current_event = None
                    exc = self._interrupt
                    self._interrupt = None
                    yielded = self._coro.throw(exc)
                else:
                    self._started = True
                    yielded = self._coro.send(value)

                # Tight loop: if the yielded event is already triggered,
                # resume the coroutine immediately without going to the heap.
                self._current_event = yielded
                v = yielded._value
                if v is not _PENDING and v is not _CANCELLED:
                    if self._interrupt is not None:
                        # An interrupt arrived while in the tight loop.
                        # Loop again so the interrupt branch above delivers it.
                        continue
                    value = v
                    self._current_event = None
                    continue

                # Event is still pending: park until it fires.
                yielded._add_waiter(self.resume)
                break

        except StopIteration:
            self._done = True
            self._current_event = None

        except Exception:
            self._done = True
            self._current_event = None
            raise

        finally:
            self._env._active_process = None

    def resume(self, value: Any = None) -> None:
        """Called by an Event when it triggers; re-schedules _loop.

        Uses functools.partial (a C-level callable) to avoid creating a Python
        closure, keeping per-resume overhead low.
        """
        if not self._done:
            self._env.immediate(partial(self._loop, value))


class Environment:
    """Discrete-event simulation environment.

    Maintains two queues:
    - _ready: callbacks to run at the current simulated time (deque).
    - _heap:  callbacks scheduled for a future time (min-heap).

    The clock only advances when popping from _heap; _ready is always drained
    first.  This prevents zero-delay events from racing ahead of same-time
    future events and ensures FIFO ordering among simultaneous events.
    """

    def __init__(self):
        self._now: float | int = 0
        self._heap: list = []
        self._ready: deque = deque()
        self._active_process: Process | None = None
        self._log: list[tuple[float | int, str, str]] = []

    @property
    def now(self) -> float | int:
        """Current simulation time."""
        return self._now

    def log(self, name: str, message: str) -> None:
        """Record a log message."""
        self._log.append((self._now, name, message))

    def get_log(self) -> list[tuple[float | int, str, str]]:
        return self._log

    def immediate(self, cb) -> None:
        """Schedule `cb` for execution at the current simulated time."""
        self._ready.append(cb)

    def schedule(self, time: float | int, cb) -> None:
        """Schedule `cb` to run at `time` in the future."""
        heapq.heappush(self._heap, (time, next(_serial), cb))

    def timeout(self, delay: float | int) -> Timeout:
        """Return a Timeout event for `delay` time units."""
        return Timeout(self, delay)

    def run(self, until: float | int | None = None) -> None:
        """Run the simulation.

        Runs until no events remain, or until simulated time reaches `until`.
        """
        while True:
            # Drain all zero-delay work before advancing the clock.
            while self._ready:
                self._ready.popleft()()

            if not self._heap:
                break

            next_time = self._heap[0][0]
            if until is not None and next_time > until:
                break

            _, _, cb = heapq.heappop(self._heap)
            result = cb()
            # _NO_TIME signals a cancelled Timeout; do not advance the clock.
            if result is not _NO_TIME and next_time > self._now:
                self._now = next_time

    def __repr__(self) -> str:
        return f"Environment(now={self._now})"
