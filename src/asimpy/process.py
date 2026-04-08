"""Abstract base class for simulation processes."""

from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any

from .event import _CANCELLED, _PENDING, Event
from .interrupt import Interrupt
from .timeout import Timeout

if TYPE_CHECKING:
    from .environment import Environment


class Process(ABC):
    """Abstract base class for all simulation processes.

    Subclasses implement run() as an async method.  Optionally override
    init() for setup that must happen before the coroutine is created.
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

    def log(self, name: str, message: str) -> None:
        """Record a log message in the environment."""
        self._env.log(name, message)

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
