"""Shared resource with limited capacity."""

from typing import TYPE_CHECKING
from .actions import BaseAction
from .process import Process

if TYPE_CHECKING:
    from .environment import Environment


class Resource:
    """Shared resource with limited capacity."""

    def __init__(self, env: "Environment", capacity: int = 1):
        """
        Create a new resource.

        Args:
            env: simulation environment.
            capacity: maximum simultaneous users.
        """
        self._env = env
        self._capacity = capacity
        self._count = 0
        self._waiting = []

    async def acquire(self):
        """Acquire one unit of the resource."""
        await _Acquire(self)

    async def release(self):
        """Release one unit of the resource."""
        await _Release(self)

    async def __aenter__(self):
        """Acquire one unit of the resource using `async with`."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Release one unit of the resource acquired with `async with`."""
        await self.release()


# ----------------------------------------------------------------------


class _Acquire(BaseAction):
    """Acquire a resource."""

    def __init__(self, resource: Resource):
        super().__init__(resource._env)
        self._resource = resource

    def act(self, proc: Process):
        if self._resource._count < self._resource._capacity:
            self._resource._count += 1
            self._env.schedule(self._env.now, proc)
        else:
            self._resource._waiting.append(proc)


class _Release(BaseAction):
    """Release a resource."""

    def __init__(self, resource: Resource):
        super().__init__(resource._env)
        self._resource = resource

    def act(self, proc: Process):
        self._resource._count -= 1
        if self._resource._waiting:
            next_proc = self._resource._waiting.pop(0)
            self._resource._count += 1
            self._env.schedule(self._env.now, next_proc)
        self._env.schedule(self._env.now, proc)
