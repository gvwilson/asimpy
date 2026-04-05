"""Wait for all of a set of events to complete."""

from typing import Any
from .core import Event


class AllOf(Event):
    """An Event that triggers when all named child Events have triggered.

    Child events are passed as keyword arguments.  The value of the AllOf
    event is a dict mapping each keyword to the corresponding result.
    """

    __slots__ = ("_events", "_results")

    def __init__(self, env, **events: Any):
        if not events:
            raise ValueError("AllOf requires at least one event")
        super().__init__(env)
        self._events: dict = {}
        self._results: dict = {}

        # First pass: validate and register all events before attaching waiters.
        # _child_done checks len(_results) == len(_events); all events must be
        # present before any pre-triggered event fires during _add_waiter.
        for key, evt in events.items():
            if not isinstance(evt, Event):
                raise TypeError(
                    f"AllOf argument {key!r} must be an Event, got {type(evt).__name__}"
                )
            self._events[key] = evt

        # Second pass: attach waiters now that _events is complete.
        for key, evt in self._events.items():
            evt._add_waiter(lambda v, k=key: self._child_done(k, v))

    def _child_done(self, key: str, value: Any) -> None:
        self._results[key] = value
        if len(self._results) == len(self._events):
            self.succeed(self._results)
