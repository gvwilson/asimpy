"""Simulation environment."""

from dataclasses import dataclass
import heapq
from typing import Awaitable
from .actions import BaseAction


class Environment:
    """Simulation environment."""

    def __init__(self):
        self.now = 0
        self._proc_id = 0  # to break ties
        self._queue = []

    def process(self, coro):
        """Start a new process immediately."""
        self.schedule(self.now, coro)
        return coro

    def sleep(self, delay):
        return _Sleep(self, delay)

    def schedule(self, time, coro):
        heapq.heappush(self._queue, _Pending(time, self._proc_id, coro))
        self._proc_id += 1

    def run(self, until=None):
        while self._queue:
            pending = heapq.heappop(self._queue)

            if until is not None and pending.time > until:
                break
            self.now = pending.time

            try:
                awaited = pending.coro.send(None)
            except StopIteration:
                continue

            awaited.act(pending.coro)


# ----------------------------------------------------------------------


@dataclass
class _Pending:
    time: float
    proc_id: int
    coro: Awaitable

    def __lt__(self, other):
        return (self.time < other.time) or (self.proc_id < other.proc_id)


class _Sleep(BaseAction):
    """Wait for a specified simulated time."""

    def __init__(self, env, delay):
        super().__init__(env)
        self.delay = delay

    def act(self, coro):
        self.env.schedule(self.env.now + self.delay, coro)
