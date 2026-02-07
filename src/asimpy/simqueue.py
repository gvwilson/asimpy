"""FIFO and priority queues."""

import heapq
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

    async def get(self):
        """Get one item from the queue."""
        if self._items:
            item = self._get_item()
            evt = Event(self._env)
            evt._on_cancel = lambda: self._items.insert(0, item)
            self._env.immediate(lambda: evt.succeed(item))
            return await evt
        else:
            evt = Event(self._env)
            self._getters.append(evt)
            return await evt

    async def put(self, item: Any):
        """
        Add one item to the queue.

        Args:
            item: to add to the queue.
        """
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
        else:
            if self._max_capacity is not None and len(self._items) >= self._max_capacity:
                return
            self._put_item(item)

    def _get_item(self):
        return self._items.pop(0)

    def _put_item(self, item):
        self._items.append(item)


class PriorityQueue(Queue):
    """Ordered queue."""

    def _get_item(self):
        return heapq.heappop(self._items)

    def _put_item(self, item):
        heapq.heappush(self._items, item)
