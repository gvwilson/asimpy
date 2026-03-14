"""FIFO and priority queues."""

import bisect
from collections import deque
from typing import TYPE_CHECKING, Any

from .event import Event, _CANCELLED
from .interrupt import Interrupt

if TYPE_CHECKING:
    from .environment import Environment


class Queue:
    """FIFO queue backed by a deque for O(1) enqueue and dequeue."""

    def __init__(
        self,
        env: "Environment",
        max_capacity: int | None = None,
    ):
        """
        Construct queue.

        Args:
            env: simulation environment.
            max_capacity: maximum queue capacity (None for unlimited).

        Raises:
            ValueError: for invalid `max_capacity`.
        """
        if max_capacity is not None and max_capacity <= 0:
            raise ValueError(
                f"queue max_capacity must be a positive integer, got {max_capacity}"
            )
        self._env = env
        self._max_capacity = max_capacity
        # _items, _getters, and _putters are all deques for O(1) front access.
        self._items: deque = deque()
        self._getters: deque = deque()
        self._putters: deque = deque()

    # ------------------------------------------------------------------
    # Overridable item-storage primitives (used by PriorityQueue)
    # ------------------------------------------------------------------

    def _add(self, item) -> None:
        self._items.append(item)

    def _pop(self):
        return self._items.popleft()

    def _put_back(self, item) -> None:
        """Return an item to the front of the store (used on interrupt)."""
        self._items.appendleft(item)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def is_empty(self) -> bool:
        """Is the queue empty?"""
        return not self._items

    def is_full(self) -> bool:
        """Has the queue reached capacity?"""
        return self._max_capacity is not None and len(self._items) >= self._max_capacity

    async def get(self):
        """Get one item from the queue."""
        if self._items:
            item = self._pop()

            # Promote one blocked putter if present, skipping cancelled ones.
            while self._putters:
                putter_evt, putter_item = self._putters[0]
                if putter_evt._value is _CANCELLED:
                    self._putters.popleft()
                    continue
                self._putters.popleft()
                self._add(putter_item)
                # Pre-trigger so the tight loop resumes the putter immediately.
                putter_evt.succeed(True)
                break

            # Pre-trigger the getter event so the tight loop resumes this
            # coroutine without a heap round-trip.
            evt = Event(self._env)
            evt.succeed(item)
            try:
                return await evt
            except Interrupt:
                # Pre-triggered events cannot really be interrupted here, but
                # restore the item defensively in case semantics change.
                self._put_back(item)
                raise
        else:
            evt = Event(self._env)
            # No _on_cancel: lazy deletion in put() skips cancelled getters.
            self._getters.append(evt)
            try:
                return await evt
            except Interrupt:
                # Don't remove from _getters; lazy deletion handles it.
                raise

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
        # Deliver directly to a waiting getter, skipping cancelled ones.
        while self._getters:
            evt = self._getters[0]
            if evt._value is _CANCELLED:
                self._getters.popleft()
                continue
            self._getters.popleft()
            evt.succeed(item)
            return True

        if not self.is_full():
            self._add(item)
            return True

        evt = Event(self._env)
        entry = (evt, item)
        self._putters.append(entry)
        # No _on_cancel: lazy deletion in get() skips cancelled putters.
        return await evt


class PriorityQueue(Queue):
    """Priority queue: items are dequeued in sorted (ascending) order."""

    def __init__(
        self,
        env: "Environment",
        max_capacity: int | None = None,
    ):
        """
        Construct priority queue.

        Args:
            env: simulation environment.
            max_capacity: maximum queue capacity (None for unlimited).

        Raises:
            ValueError: for invalid `max_capacity`.
        """
        super().__init__(env, max_capacity)
        # Override the deque with a sorted list.
        self._items: list = []  # type: ignore[assignment]

    def _add(self, item) -> None:
        bisect.insort(self._items, item)

    def _pop(self):
        return self._items.pop(0)

    def _put_back(self, item) -> None:
        bisect.insort(self._items, item)

    def is_empty(self) -> bool:
        return not self._items

    def is_full(self) -> bool:
        return self._max_capacity is not None and len(self._items) >= self._max_capacity
