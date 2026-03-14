"""Simulation environment."""

from collections import deque
import heapq
import itertools
from typing import TYPE_CHECKING

from .timeout import _NO_TIME, Timeout

if TYPE_CHECKING:
    from .process import Process

# Module-level counter for heap entry tiebreaking (ensures FIFO ordering
# among events at identical simulation times without comparing callbacks).
_serial = itertools.count()


class Environment:
    """Simulation environment."""

    def __init__(self):
        self._now = 0
        # Heap of (time, serial, callback) for future-time events.
        self._heap: list = []
        # Deque of callbacks ready to run at the current time.
        # Drained completely before advancing the clock.
        self._ready: deque = deque()
        self.active_process: "Process | None" = None
        """The process currently executing, or None between events."""

    @property
    def now(self):
        """Get the current simulated time."""
        return self._now

    def immediate(self, callback) -> None:
        """Schedule a callback for execution at the current time."""
        self._ready.append(callback)

    def schedule(self, time, callback) -> None:
        """Schedule a callback to run at a specified future time."""
        heapq.heappush(self._heap, (time, next(_serial), callback))

    def run(self, until=None) -> None:
        """Run simulation."""
        while True:
            # Drain every callback that is ready at the current time before
            # advancing the clock.  New entries may be appended to _ready
            # while we iterate, and they will be picked up in the same pass.
            while self._ready:
                self._ready.popleft()()

            if not self._heap:
                break

            # Peek at the earliest future event.
            time = self._heap[0][0]
            if until is not None and time > until:
                break

            _, _, callback = heapq.heappop(self._heap)
            result = callback()
            # _NO_TIME is returned by a cancelled Timeout._fire(); in that
            # case the clock must not advance (the event was a phantom).
            if result is not _NO_TIME and time > self._now:
                self._now = time

    def timeout(self, delay):
        """Create delay."""
        return Timeout(self, delay)

    def __str__(self):
        return f"Env(t={self._now})"
