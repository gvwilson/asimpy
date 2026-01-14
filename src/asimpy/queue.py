"""FIFO and priority queues."""

import heapq
from typing import TYPE_CHECKING, Any
from .event import Event

if TYPE_CHECKING:
    from .environment import Environment

class Queue:
    """FIFO queue."""

    def __init__(self, env: "Environment"):
        """
        Construct queue.

        Args:
            env: simulation environment.
        """
        self._env = env
        self._items = []
        self._getters = []

    async def get(self):
        """Get one item from the queue."""
        if self._items:
            item = self._items.pop(0)
            evt = Event(self._env)
            self._env._immediate(lambda: evt.succeed(item))
            evt._on_cancel = lambda: self._items.insert(0, item)
            return await evt

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
            self._items.append(item)


class PriorityQueue(Queue):
    """Ordered queue."""

    async def put(self, item: Any):
        """
        Add one item to the queue.

        Args:
            item: comparable item to add to queue.
        """
        heapq.heappush(self._items, item)
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(heapq.heappop(self._items))
