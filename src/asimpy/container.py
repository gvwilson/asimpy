"""Homogeneous resource (continuous or discrete amounts)."""

from typing import Union
from .core import _CANCELLED, Event

Amount = Union[int, float]


class ContainerEmpty(Exception):
    """Raised by Container.try_get() when there is insufficient content."""


class ContainerFull(Exception):
    """Raised by Container.try_put() when there is insufficient space."""


class Container:
    """A resource holding up to *capacity* units of homogeneous content.

    Works for both continuous amounts (float) and discrete counts (int).
    Blocking operations return an Event whose value is the amount transferred.
    Non-blocking operations raise on failure.

    Cancelled get events restore the level via _on_cancel so that FirstOf
    does not silently discard consumed content.
    """

    def __init__(
        self,
        env,
        capacity: Amount = float("inf"),
        init: Amount = 0,
    ):
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        if init < 0:
            raise ValueError(f"init must be non-negative, got {init}")
        if init > capacity:
            raise ValueError(f"init ({init}) must be <= capacity ({capacity})")
        self._env = env
        self._capacity = capacity
        self._level: Amount = init
        # Each entry is [amount, Event].
        self._getters: list = []
        self._putters: list = []

    @property
    def level(self) -> Amount:
        """Current content level."""
        return self._level

    @property
    def capacity(self) -> Amount:
        """Maximum capacity."""
        return self._capacity

    # ------------------------------------------------------------------
    # Blocking operations (return Event)
    # ------------------------------------------------------------------

    def get(self, amount: Amount) -> Event:
        """Return an Event that resolves to *amount* when content is available.

        If sufficient content is available immediately, the Event is
        pre-triggered and _on_cancel is set to restore the level if FirstOf
        later discards the result.
        """
        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")
        if self._level >= amount:
            self._level -= amount
            self._trigger_putters()
            evt = Event(self._env)
            evt._on_cancel = lambda v: self._undo_get(v)
            evt.succeed(amount)
            return evt

        evt = Event(self._env)
        self._getters.append([amount, evt])
        return evt

    def put(self, amount: Amount) -> Event:
        """Return an Event that resolves to *amount* when space is available."""
        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")
        if self._level + amount <= self._capacity:
            self._level += amount
            self._trigger_getters()
            evt = Event(self._env)
            evt.succeed(amount)
            return evt

        evt = Event(self._env)
        self._putters.append([amount, evt])
        return evt

    # ------------------------------------------------------------------
    # Non-blocking operations (raise on failure)
    # ------------------------------------------------------------------

    def try_get(self, amount: Amount) -> Amount:
        """Remove and return *amount* of content, or raise ContainerEmpty."""
        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")
        if self._level < amount:
            raise ContainerEmpty(f"requested {amount}, available {self._level}")
        self._level -= amount
        return amount

    def try_put(self, amount: Amount) -> None:
        """Add *amount* of content, or raise ContainerFull."""
        if amount <= 0:
            raise ValueError(f"amount must be positive, got {amount}")
        if self._level + amount > self._capacity:
            raise ContainerFull(
                f"adding {amount} would exceed capacity {self._capacity}"
            )
        self._level += amount

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _trigger_getters(self) -> None:
        """Satisfy as many pending getters as the current level allows."""
        i = 0
        while i < len(self._getters):
            amount, evt = self._getters[i]
            if evt._value is _CANCELLED:
                self._getters.pop(i)
                continue
            if self._level >= amount:
                self._level -= amount
                self._getters.pop(i)
                # Set _on_cancel before succeed() so cancel() can restore
                # the level even after the event has been triggered.
                evt._on_cancel = lambda v: self._undo_get(v)
                evt.succeed(amount)
            else:
                i += 1

    def _trigger_putters(self) -> None:
        """Satisfy as many pending putters as capacity allows."""
        i = 0
        while i < len(self._putters):
            amount, evt = self._putters[i]
            if evt._value is _CANCELLED:
                self._putters.pop(i)
                continue
            if self._level + amount <= self._capacity:
                self._level += amount
                self._putters.pop(i)
                evt.succeed(amount)
            else:
                i += 1

    def _undo_get(self, amount: Amount) -> None:
        """Restore *amount* to the level after a get is cancelled."""
        self._level += amount
