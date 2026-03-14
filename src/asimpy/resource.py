"""Shared resource with limited capacity."""

from collections import deque
from typing import TYPE_CHECKING

from .event import Event, _CANCELLED

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
        if capacity <= 0:
            raise ValueError(f"resource capacity must be positive, got {capacity}")
        self._env = env
        self.capacity = capacity
        self._count = 0
        # deque gives O(1) popleft instead of O(n) list.pop(0).
        self._waiters: deque = deque()

    async def acquire(self):
        """Acquire one unit of resource."""
        if self._count < self.capacity:
            await self._acquire_available()
        else:
            await self._acquire_unavailable()

    def release(self):
        """Release one unit of resource."""
        self._count -= 1
        # Lazy deletion: skip waiters that were cancelled while queued.
        while self._waiters:
            evt = self._waiters[0]
            if evt._value is _CANCELLED:
                self._waiters.popleft()
                continue
            self._waiters.popleft()
            evt.succeed()
            self._count += 1
            break

    async def _acquire_available(self):
        self._count += 1
        evt = Event(self._env)
        # Pre-trigger so the tight loop in Process._loop resumes without
        # going through the heap.  The event is already triggered, so
        # cancellation is a no-op and _on_cancel is not needed.
        evt.succeed()
        await evt

    async def _acquire_unavailable(self):
        evt = Event(self._env)
        # No _on_cancel: lazy deletion in release() handles cancelled entries.
        self._waiters.append(evt)
        await evt
        self._count += 1

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.release()
