"""FIFO and priority queues."""

import bisect
from typing import TYPE_CHECKING, Any
from .event import Event

if TYPE_CHECKING:
    from .environment import Environment


class Queue:
    """FIFO or priority queue."""

    def __init__(self, env: "Environment", max_capacity: int | None = None,
                 priority: bool = False):
        """
        Construct queue.

        Args:
            env: simulation environment.
            max_capacity: maximum queue capacity (None for unlimited).
            priority: if `True`, maintain items in sorted order.
        """
        if max_capacity is not None:
            assert max_capacity > 0, "max_capacity must be a positive integer"
        self._env = env
        self._priority = priority
        self._max_capacity = max_capacity
        self._items = []
        self._getters = []

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

    def put(self, item: Any) -> bool:
        """
        Add one item to the queue.

        If a getter is waiting, the item is delivered directly.
        Otherwise, if the queue is not full, the item is added.
        If the queue is full, the item is discarded (in priority
        mode, the lowest-priority item is discarded instead).

        Args:
            item: to add to the queue.

        Returns:
            `True` if item added, `False` otherwise.
        """
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
            return True

        if not self.is_full():
            if self._priority:
                bisect.insort(self._items, item)
            else:
                self._items.append(item)
            return True

        if not self._priority:
            return False

        bisect.insort(self._items, item)
        result = item is not self._items[-1]
        self._items = self._items[:self._max_capacity]
        return result


class BlockingQueue:
    """FIFO queue with blocking put when at capacity."""

    def __init__(self, env: "Environment", max_capacity: int):
        """
        Construct blocking queue.

        Args:
            env: simulation environment.
            max_capacity: maximum queue capacity (must be a positive integer).
        """
        assert isinstance(max_capacity, int), "max_capacity must be an integer"
        assert max_capacity > 0, "max_capacity must be a positive integer"
        self._env = env
        self._max_capacity = max_capacity
        self._items = []
        self._getters = []
        self._putters = []

    async def get(self):
        """Get one item from the queue."""
        if self._items:
            item = self._items.pop(0)
            if self._putters:
                putter_evt, putter_item = self._putters.pop(0)
                self._items.append(putter_item)
                self._env.immediate(lambda evt=putter_evt: evt.succeed(True))
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
        return len(self._items) >= self._max_capacity

    async def put(self, item: Any) -> bool:
        """
        Add one item to the queue.

        If a getter is waiting, the item is delivered directly.
        Otherwise, if the queue is not full, the item is added.
        If the queue is full, the operation blocks until space
        is available.

        Args:
            item: to add to the queue.

        Returns:
            `True` when the item has been added.
        """
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
            return True

        if not self.is_full():
            self._items.append(item)
            return True

        evt = Event(self._env)
        entry = (evt, item)
        self._putters.append(entry)

        def cancel():
            if entry in self._putters:
                self._putters.remove(entry)

        evt._on_cancel = cancel
        return await evt
