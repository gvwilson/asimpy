"""Shared resource with limited capacity (discrete slots)."""

from collections import deque
from .core import _CANCELLED, Event


class Resource:
    """A shared resource with *capacity* concurrent-use slots.

    Processes acquire a slot (blocking if all slots are taken) and release it
    when done.  Supports async context manager protocol.
    """

    def __init__(self, env, capacity: int = 1):
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._env = env
        self.capacity = capacity
        self._count = 0
        self._waiters: deque = deque()  # pending Event objects

    @property
    def count(self) -> int:
        """Number of slots currently in use."""
        return self._count

    # ------------------------------------------------------------------
    # Blocking acquire (returns Event)
    # ------------------------------------------------------------------

    def acquire(self) -> Event:
        """Return an Event that resolves to None when a slot is available."""
        if self._count < self.capacity:
            self._count += 1
            evt = Event(self._env)
            # _on_cancel restores the slot if FirstOf later discards this event.
            evt._on_cancel = lambda v: self.release()
            evt.succeed()
            return evt

        evt = Event(self._env)
        self._waiters.append(evt)
        return evt

    # ------------------------------------------------------------------
    # Non-blocking acquire
    # ------------------------------------------------------------------

    def try_acquire(self) -> bool:
        """Acquire a slot if one is free.  Returns True on success, False otherwise."""
        if self._count < self.capacity:
            self._count += 1
            return True
        return False

    # ------------------------------------------------------------------
    # Release (synchronous)
    # ------------------------------------------------------------------

    def release(self) -> None:
        """Release one slot and wake the next waiting process (lazy deletion)."""
        self._count -= 1
        while self._waiters:
            evt = self._waiters[0]
            if evt._value is _CANCELLED:
                self._waiters.popleft()
                continue
            self._waiters.popleft()
            self._count += 1
            evt.succeed()
            break

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "Resource":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.release()
