"""FIFO and priority queues."""

import bisect
from typing import TYPE_CHECKING, Any
from .event import Event

if TYPE_CHECKING:
    from .environment import Environment


class Queue:
    """FIFO queue."""

    def __init__(self, env: "Environment", max_capacity: int | None = None):
        """
        Construct queue.

        Args:
            env: simulation environment.
            max_capacity: maximum queue capacity (None for unlimited).
        """
        if max_capacity is not None:
            assert max_capacity > 0, "max_capacity must be a positive integer"
        self._env = env
        self._max_capacity = max_capacity
        self._items = []
        self._getters = []
        self._dropped = 0

    async def get(self):
        """Get one item from the queue."""
        if self._items:
            item = self._items.pop(0)
            evt = Event(self._env)
            evt._on_cancel = lambda: self._items.insert(0, item)
            self._env.immediate(lambda: evt.succeed(item))
            return await evt
        else:
            evt = Event(self._env)
            self._getters.append(evt)
            return await evt

    def is_full(self):
        """Has the queue reached capacity?"""
        return self._max_capacity is not None and len(self._items) >= self._max_capacity

    async def put(self, item: Any):
        """
        Add one item to the queue (if there is capacity).

        Args:
            item: to add to the queue.
        """
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
        else:
            if self.is_full():
                self._dropped += 1
                return
            self._items.append(item)


class PriorityQueue(Queue):
    """Ordered queue."""

    async def put(self, item: Any):
        """
        Add one item to the queue (if there is capacity).  If there is
        not capacity, either discard a lower-priority item or discard
        this one.

        Args:
            item: to add to the queue.
        """
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
        else:
            bisect.insort(self._items, item)
            if (self._max_capacity is not None) and (len(self._items) > self._max_capacity):
                self._dropped += 1
                self._items = self._items[:self._max_capacity]
