"""FIFO queues with blocking and non-blocking operations."""

import bisect
from collections import deque
from typing import Any
from .core import _CANCELLED, Event


class QueueEmpty(Exception):
    """Raised by Queue.try_get() when the queue is empty."""


class QueueFull(Exception):
    """Raised by Queue.try_put() when the queue is at capacity."""


class Queue:
    """FIFO queue with optional maximum capacity.

    Blocking operations (get, put) return an Event; await it for the result.
    Non-blocking operations (try_get, try_put) raise on failure.
    """

    def __init__(self, env, capacity: int | None = None):
        if capacity is not None and capacity <= 0:
            raise ValueError(f"capacity must be a positive integer, got {capacity}")
        self._env = env
        self._capacity = capacity
        self._items: deque = deque()
        self._getters: deque = deque()  # pending Event objects
        self._putters: deque = deque()  # (Event, item) pairs

    # ------------------------------------------------------------------
    # Internal storage helpers (overridden by PriorityQueue)
    # ------------------------------------------------------------------

    def _add(self, item: Any) -> None:
        """Add item to the internal store."""
        self._items.append(item)

    def _pop(self) -> Any:
        """Remove and return the next item from the internal store."""
        return self._items.popleft()

    def _put_back(self, item: Any) -> None:
        """Return a previously removed item to the front of the store."""
        self._items.appendleft(item)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_empty(self) -> bool:
        """True if the queue has no items."""
        return not self._items

    def is_full(self) -> bool:
        """True if the queue is at capacity."""
        return self._capacity is not None and len(self._items) >= self._capacity

    def size(self) -> int:
        """Number of items currently in the queue."""
        return len(self._items)

    # ------------------------------------------------------------------
    # Blocking operations (return Event)
    # ------------------------------------------------------------------

    def get(self) -> Event:
        """Return an Event whose value is the next dequeued item."""
        if self._items:
            item = self._pop()
            self._promote_putter()
            evt = Event(self._env)
            evt._on_cancel = lambda v: self._put_back(v)
            evt.succeed(item)
            return evt

        evt = Event(self._env)
        self._getters.append(evt)
        return evt

    def put(self, item: Any) -> Event:
        """Return an Event that resolves to True when `item` is enqueued.

        Delivers directly to a waiting getter if one exists, adds to the
        queue if there is capacity, or blocks until capacity becomes available.
        """
        # Deliver directly to a non-cancelled waiting getter.
        while self._getters:
            getter = self._getters[0]
            if getter._value is _CANCELLED:
                self._getters.popleft()
                continue
            self._getters.popleft()
            getter._on_cancel = lambda v: self._put_back(v)
            getter.succeed(item)
            result = Event(self._env)
            result.succeed(True)
            return result

        if not self.is_full():
            self._add(item)
            result = Event(self._env)
            result.succeed(True)
            return result

        evt = Event(self._env)
        self._putters.append((evt, item))
        return evt

    # ------------------------------------------------------------------
    # Non-blocking operations (raise on failure)
    # ------------------------------------------------------------------

    def try_get(self) -> Any:
        """Remove and return the next item, or raise QueueEmpty."""
        if self._items:
            return self._pop()
        raise QueueEmpty("queue is empty")

    def try_put(self, item: Any) -> None:
        """Add `item` to the queue, or raise QueueFull."""
        if self.is_full():
            raise QueueFull("queue is at capacity")
        self._add(item)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _promote_putter(self) -> None:
        """Move one waiting putter's item into the queue (lazy deletion)."""
        while self._putters:
            evt, item = self._putters[0]
            if evt._value is _CANCELLED:
                self._putters.popleft()
                continue
            self._putters.popleft()
            self._add(item)
            evt.succeed(True)
            break


class PriorityQueue(Queue):
    """Queue that serves items in sorted (ascending) order.

    Uses bisect.insort to maintain the internal list in sorted order.
    Items must be comparable.
    """

    def __init__(self, env, capacity: int | None = None):
        super().__init__(env, capacity)
        # Use a plain list for bisect operations instead of a deque.
        self._items: list = []

    def _add(self, item: Any) -> None:
        """Insert item in sorted order."""
        bisect.insort(self._items, item)

    def _pop(self) -> Any:
        """Remove and return the smallest item."""
        return self._items.pop(0)

    def _put_back(self, item: Any) -> None:
        """Re-insert a cancelled item in sorted order."""
        bisect.insort(self._items, item)
