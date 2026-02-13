"""Shared resource with limited capacity."""

from typing import TYPE_CHECKING
from .event import Event
from ._utils import _validate

if TYPE_CHECKING:
    from .environment import Environment


class Resource:
    """A shared resource with limited capacity."""

    def __init__(self, env: "Environment", capacity: int = 1):
        """
        Construct resource.

        Args:
            env: simulation environment.
            capacity: maximum capacity.

        Raises:
            ValueError: for invalid `capacity`.
        """
        _validate(capacity > 0, "require positive capacity for resource not {capacity}")
        self._env = env
        self.capacity = capacity
        self._count = 0
        self._waiters = []

    async def acquire(self):
        """Acquire one unit of resource."""
        if self._count < self.capacity:
            await self._acquire_available()
        else:
            await self._acquire_unavailable()

    async def release(self):
        """Release one unit of resource."""
        self._count -= 1
        if self._waiters:
            evt = self._waiters.pop(0)
            evt.succeed()

    async def _acquire_available(self):
        def cancel():
            self._count -= 1

        self._count += 1
        evt = Event(self._env)
        evt._on_cancel = cancel
        self._env.immediate(evt.succeed)
        await evt

    async def _acquire_unavailable(self):
        evt = Event(self._env)

        def cancel():
            if evt in self._waiters:
                self._waiters.remove(evt)

        self._waiters.append(evt)
        evt._on_cancel = cancel
        await evt
        self._count += 1

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()
