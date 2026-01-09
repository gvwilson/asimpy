"""Shared resource."""

from collections import deque
from .actions import Acquire, Release


class Resource:
    """Shared resource with limited capacity."""

    def __init__(self, env, capacity=1):
        self.env = env
        self.capacity = capacity
        self.in_use = 0
        self.queue = deque()

    async def acquire(self):
        await Acquire(self.env, self)

    async def release(self):
        await Release(self.env, self)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()
