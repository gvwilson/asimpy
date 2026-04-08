"""Discrete-event simulation environment."""

from collections import deque
import heapq
import itertools
from typing import TYPE_CHECKING

from .event import Event
from .timeout import _NO_TIME, Timeout

if TYPE_CHECKING:
    from .process import Process

# Tiebreaker counter for heap entries at the same simulation time.
_serial = itertools.count()


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
        self._active_process: "Process | None" = None
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
