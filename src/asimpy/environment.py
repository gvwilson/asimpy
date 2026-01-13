"""Simulation environment."""

from dataclasses import dataclass, field
import heapq
from typing import Callable


@dataclass(order=True)
class _Pending:
    time: float
    callback: Callable = field(compare=False)


class Environment:
    def __init__(self, logging=False):
        self.now = 0
        self._queue = []
        self._logging = logging

    def schedule(self, time, callback):
        heapq.heappush(self._queue, _Pending(time, callback))

    def immediate(self, callback):
        self.schedule(self.now, callback)

    def timeout(self, delay):
        from .event import Timeout

        return Timeout(self, delay)

    def run(self, until=None):
        while self._queue:
            pending = heapq.heappop(self._queue)
            if until is not None and pending.time > until:
                break
            self.now = pending.time
            pending.callback()

    def __str__(self):
        return f"Env(t={self.now})"
