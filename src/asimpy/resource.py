"""Shared resource."""

from collections import deque
from .actions import BaseAction


class Resource:
    """Shared resource with limited capacity."""

    def __init__(self, env, capacity=1):
        self.env = env
        self.capacity = capacity
        self.in_use = 0
        self.queue = deque()

    async def acquire(self):
        await _Acquire(self)

    async def release(self):
        await _Release(self)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()


# ----------------------------------------------------------------------


class _Acquire(BaseAction):
    """Acquire a resource."""

    def __init__(self, resource):
        super().__init__(resource.env)
        self.resource = resource

    def act(self, coro):
        if self.resource.in_use < self.resource.capacity:
            self.resource.in_use += 1
            self.env.schedule(self.env.now, coro)
        else:
            self.resource.queue.append(coro)


class _Release(BaseAction):
    """Release a resource."""

    def __init__(self, resource):
        super().__init__(resource.env)
        self.resource = resource

    def act(self, coro):
        self.resource.in_use -= 1
        if self.resource.queue:
            next_coro = self.resource.queue.popleft()
            self.resource.in_use += 1
            self.env.schedule(self.env.now, next_coro)
        self.env.schedule(self.env.now, coro)
