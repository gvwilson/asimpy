from dataclasses import dataclass, field
import heapq
from itertools import count
from typing import Callable

from timeout import Timeout


class Environment:
    """Simulation environment and event scheduler."""

    def __init__(self):
        self._now = 0
        self._pending = []

    @property
    def now(self):
        return self._now

    def schedule(self, time: float, callback: Callable[[], None]):
        heapq.heappush(self._pending, _Pending(time, callback))

    def timeout(self, delay: float | int):
        return Timeout(self, delay)

    def run(self, until=None):
        """Run the simulation."""
        while self._pending:
            pending = heapq.heappop(self._pending)
            if until is not None and pending.time > until:
                break
            self._now = pending.time
            pending.callback()

    def _immediate(self, callback: Callable[[], None]):
        """Schedule callback at current simulation time."""
        self.schedule(self._now, callback)


@dataclass(order=True)
class _Pending:
    _counter = count()

    time: float
    serial: int = field(init=False, repr=False)
    callback: Callable = field(compare=False)

    def __post_init__(self):
        self.serial = next(self._counter)
