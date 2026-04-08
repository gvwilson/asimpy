"""Awaitable simulation event."""

from typing import Any

# Sentinels stored in Event._value to represent lifecycle state.
_PENDING = object()  # event has not yet been triggered or cancelled
_CANCELLED = object()  # event was cancelled


class Event:
    """An awaitable simulation event.

    Primitives such as Queue.get() return Event objects.  Processes suspend
    themselves by awaiting an Event:

        item = await queue.get()

    An Event transitions through these states (stored in _value):
        _PENDING: not yet triggered
        any value: triggered with that value (including None)
        _CANCELLED: cancelled; _on_cancel was called if set

    The _on_cancel callback is called by cancel() even when the event has
    already been triggered.  This lets resource-consuming get() methods
    restore their resource when FirstOf discards a non-winning event.
    """

    __slots__ = ("_env", "_value", "_waiters", "_on_cancel")

    def __init__(self, env: "Environment"):
        self._env = env
        self._value: Any = _PENDING
        self._waiters: list = []
        self._on_cancel = None

    @property
    def triggered(self) -> bool:
        """True if the event has been triggered (not pending, not cancelled)."""
        v = self._value
        return v is not _PENDING and v is not _CANCELLED

    @property
    def cancelled(self) -> bool:
        """True if the event has been cancelled."""
        return self._value is _CANCELLED

    def succeed(self, value: Any = None) -> None:
        """Trigger the event with `value` and notify all waiters."""
        if self._value is not _PENDING:
            return
        self._value = value
        waiters, self._waiters = self._waiters, []
        for cb in waiters:
            cb(value)

    def fail(self, exc: Exception) -> None:
        """Trigger the event with an exception.

        The process awaiting this event will re-raise `exc`.
        """
        if not isinstance(exc, BaseException):
            raise TypeError(f"{exc!r} is not an exception")
        self.succeed(exc)

    def cancel(self) -> None:
        """Cancel the event.

        Fires _on_cancel(old_value) regardless of whether the event was
        pending or already triggered.  This ensures that resources consumed
        by a pre-triggered get event are restored when FirstOf discards it.
        Does nothing if the event is already cancelled.
        """
        if self._value is _CANCELLED:
            return
        old_value = self._value
        self._value = _CANCELLED
        self._waiters = []
        if self._on_cancel is not None:
            self._on_cancel(old_value)

    def _add_waiter(self, cb) -> None:
        """Register `cb` to be called when the event is triggered.

        If already triggered, calls `cb` immediately.
        If cancelled, the call is silently dropped.
        """
        v = self._value
        if v is _PENDING:
            self._waiters.append(cb)
        elif v is not _CANCELLED:
            cb(v)

    def __await__(self):
        value = yield self
        if isinstance(value, BaseException):
            raise value
        return value
