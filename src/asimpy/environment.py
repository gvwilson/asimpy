"""Simulation environment."""

from dataclasses import dataclass, field
import heapq
import itertools
from typing import Callable

from .event import NO_TIME
from .timeout import Timeout


class Environment:
    """Simulation environment."""

    def __init__(self):
        self._now = 0
        self._pending = []

    @property
    def now(self):
        return self._now

    def schedule(self, time, callback):
        heapq.heappush(self._pending, _Pending(time, callback))

    def timeout(self, delay):
        return Timeout(self, delay)

    def run(self, until=None):
        while self._pending:
            pending = heapq.heappop(self._pending)
            if until is not None and pending.time > until:
                break
            result = pending.callback()
            if (result is not NO_TIME) and (pending.time > self._now):
                self._now = pending.time

    def _immediate(self, callback):
        self.schedule(self._now, callback)

    def __str__(self):
        return f"Env(t={self._now})"


@dataclass(order=True)
class _Pending:
    _counter = itertools.count()

    time: float
    serial: int = field(init=False, repr=False, compare=True)
    callback: Callable = field(compare=False)

    def __post_init__(self):
        self.serial = next(self._counter)
