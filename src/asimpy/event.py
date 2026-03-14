"""Events."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .environment import Environment

# Sentinels for event state stored in _value.
# _PENDING  : event has not yet been triggered or cancelled.
# _CANCELLED: event was cancelled; waiters were already discarded.
_PENDING = object()
_CANCELLED = object()


class Event:
    """Manage an event."""

    __slots__ = ("_env", "_value", "_waiters", "_on_cancel")

    def __init__(self, env: "Environment"):
        """
        Construct a new event.

        Args:
            env: simulation environment.
        """
        self._env = env
        self._value: Any = _PENDING
        self._waiters: list = []
        self._on_cancel = None

    # ------------------------------------------------------------------
    # State helpers (properties so external code stays readable)
    # ------------------------------------------------------------------

    @property
    def _triggered(self) -> bool:
        v = self._value
        return v is not _PENDING and v is not _CANCELLED

    @property
    def _cancelled(self) -> bool:
        return self._value is _CANCELLED

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def succeed(self, value: Any = None) -> None:
        """
        Trigger the event with a value.

        Args:
            value: value associated with event.
        """
        if self._value is not _PENDING:
            return
        self._value = value
        waiters = self._waiters
        self._waiters = []          # detach before iterating (re-entrancy safety)
        for callback in waiters:
            callback(value)

    def cancel(self) -> None:
        """Cancel event."""
        if self._value is not _PENDING:
            return
        self._value = _CANCELLED
        self._waiters = []
        if self._on_cancel:
            self._on_cancel()

    def _add_waiter(self, callback) -> None:
        v = self._value
        if v is _PENDING:
            self._waiters.append(callback)
        elif v is not _CANCELLED:
            # Already triggered — call immediately.
            callback(v)
        # If cancelled, drop silently.

    def __await__(self):
        value = yield self
        return value
