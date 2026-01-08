"""Simulation environment."""

import heapq
from .events import Sleep


class Environment:
    """Simulation environment."""

    def __init__(self):
        self.now = 0
        self._task_id = 0  # to break ties
        self._queue = []  # (time, task_id, coroutine)

    def process(self, coro):
        """Start a new process immediately."""
        self.schedule(self.now, coro)

    def sleep(self, delay):
        return Sleep(self, delay)

    def schedule(self, time, coro):
        heapq.heappush(self._queue, (time, self._task_id, coro))
        self._task_id += 1

    def run(self, until=None):
        while self._queue:
            time, _, coro = heapq.heappop(self._queue)

            if until is not None and time > until:
                break
            self.now = time

            try:
                awaited = coro.send(None)
            except StopIteration:
                continue

            awaited.act(coro)
