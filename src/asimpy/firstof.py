"""Wait for the first of a set of events to complete."""

from typing import Any
from .event import Event


class FirstOf(Event):
    """An Event that triggers when the first named child Event triggers.

    The value of the FirstOf event is a (key, value) tuple identifying which
    child won and what its value was.  All other child events are cancelled.
    """

    __slots__ = ("_finished", "_events")

    def __init__(self, env, **events: Any):
        if not events:
            raise ValueError("FirstOf requires at least one event")
        super().__init__(env)
        self._finished = False
        self._events: dict = {}

        # First pass: validate and register all events before attaching waiters.
        # A pre-triggered event fires immediately inside _add_waiter, so
        # _child_done must see the full _events dict to cancel all non-winners.
        for key, evt in events.items():
            if not isinstance(evt, Event):
                raise TypeError(
                    f"FirstOf argument {key!r} must be an Event, got {type(evt).__name__}"
                )
            self._events[key] = evt

        # Second pass: attach waiters now that _events is complete.
        for key, evt in self._events.items():
            evt._add_waiter(lambda v, k=key, e=evt: self._child_done(k, v, e))

    def _child_done(self, key: str, value: Any, winner: Event) -> None:
        if self._finished:
            return
        self._finished = True

        # Cancel all non-winning events.  cancel() restores any resources
        # already consumed by pre-triggered get events via _on_cancel.
        for evt in self._events.values():
            if evt is not winner:
                evt.cancel()

        self.succeed((key, value))
