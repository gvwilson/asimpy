"""Store of heterogeneous objects with optional filter on get."""

from typing import Any, Callable
from .event import _CANCELLED, Event


class StoreEmpty(Exception):
    """Raised by Store.try_get() when no matching item is available."""


class StoreFull(Exception):
    """Raised by Store.try_put() when the store is at capacity."""


class Store:
    """A collection of heterogeneous objects.

    Blocking get() accepts an optional filter callable.  The first item for
    which filter(item) is True (or any item when filter is None) is removed
    and returned.  If no matching item is available, the process blocks.

    Blocking put() blocks only if the store is at capacity.
    """

    def __init__(self, env, capacity: int | float = float("inf")):
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._env = env
        self._capacity = capacity
        self._items: list = []
        self._getters: list = []  # Each getter entry: [filter_fn_or_None, Event]
        self._putters: list = []  # Each putter entry: [item, Event]

    def __len__(self) -> int:
        return len(self._items)

    # ------------------------------------------------------------------
    # Blocking operations (return Event)
    # ------------------------------------------------------------------

    def get(self, filter: Callable[[Any], bool] | None = None) -> Event:
        """Return an Event whose value is the first matching item.

        If a matching item is already available, the Event is pre-triggered
        and _on_cancel is set so that FirstOf can restore the item.
        """
        for i, item in enumerate(self._items):
            if filter is None or filter(item):
                self._items.pop(i)
                self._promote_putter()
                evt = Event(self._env)
                evt._on_cancel = lambda v: self._items.append(v)
                evt.succeed(item)
                return evt

        evt = Event(self._env)
        self._getters.append([filter, evt])
        return evt

    def put(self, item: Any) -> Event:
        """Return an Event that resolves to True when `item` is stored.

        Delivers directly to a matching waiting getter if one exists,
        adds to items if there is capacity, or blocks.
        """
        # Deliver directly to the first non-cancelled getter whose filter matches.
        i = 0
        while i < len(self._getters):
            filt, getter = self._getters[i]
            if getter._value is _CANCELLED:
                self._getters.pop(i)
                continue
            if filt is None or filt(item):
                self._getters.pop(i)
                getter._on_cancel = lambda v: self._items.append(v)
                getter.succeed(item)
                result = Event(self._env)
                result.succeed(True)
                return result
            i += 1

        if len(self._items) < self._capacity:
            self._items.append(item)
            result = Event(self._env)
            result.succeed(True)
            return result

        evt = Event(self._env)
        self._putters.append([item, evt])
        return evt

    # ------------------------------------------------------------------
    # Non-blocking operations (raise on failure)
    # ------------------------------------------------------------------

    def try_get(self, filter: Callable[[Any], bool] | None = None) -> Any:
        """Remove and return the first matching item, or raise StoreEmpty."""
        for i, item in enumerate(self._items):
            if filter is None or filter(item):
                return self._items.pop(i)
        raise StoreEmpty("no matching item available")

    def try_put(self, item: Any) -> None:
        """Add `item` to the store, or raise StoreFull."""
        if len(self._items) >= self._capacity:
            raise StoreFull("store is at capacity")
        self._items.append(item)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _promote_putter(self) -> None:
        """Move one waiting putter's item into the store (lazy deletion)."""
        i = 0
        while i < len(self._putters):
            item, evt = self._putters[i]
            if evt._value is _CANCELLED:
                self._putters.pop(i)
                continue
            self._putters.pop(i)
            self._items.append(item)
            evt.succeed(True)
            break
