"""Simulation environment."""

import heapq
from .events import Acquire, Release, Sleep


class Environment:
    """Simulation environment."""

    def __init__(self):
        self.now = 0
        self._task_id = 0  # to break ties
        self._queue = []  # (time, task_id, coroutine)

    def process(self, coro):
        """Start a new process immediately."""
        self._schedule(self.now, coro)

    def sleep(self, delay):
        return Sleep(delay)

    def _schedule(self, time, coro):
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

            if isinstance(awaited, Sleep):
                self._schedule(self.now + awaited.delay, coro)

            elif isinstance(awaited, Acquire):
                res = awaited.resource
                if res.in_use < res.capacity:
                    res.in_use += 1
                    self._schedule(self.now, coro)
                else:
                    res.queue.append(coro)

            elif isinstance(awaited, Release):
                res = awaited.resource
                res.in_use -= 1
                if res.queue:
                    next_coro = res.queue.popleft()
                    res.in_use += 1
                    self._schedule(self.now, next_coro)
                self._schedule(self.now, coro)

            else:
                raise RuntimeError(f"Unknown awaitable: {awaited}")
