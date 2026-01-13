"""Shared resource."""

from .event import Event


class Resource:
    def __init__(self, env, capacity=1):
        self.env = env
        self.capacity = capacity
        self.count = 0
        self._waiters = []

    async def acquire(self):
        if self.count < self.capacity:
            self.count += 1
            return
        ev = Event(self.env)
        self._waiters.append(ev)
        await ev
        self.count += 1

    async def release(self):
        self.count -= 1
        if self._waiters:
            ev = self._waiters.pop(0)
            ev.succeed()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()
