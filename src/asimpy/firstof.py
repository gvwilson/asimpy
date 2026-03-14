"""Wait for the first of a set of events."""

from typing import Any
from .environment import Environment
from .event import Event
from ._utils import _ensure_event


class FirstOf(Event):
    """Wait for the first of a set of events."""

    # _finished avoids shadowing any future Event attribute named _done.
    __slots__ = ("_finished", "_events")

    def __init__(self, env: Environment, **events: Any):
        """
        Construct new collective wait.

        Args:
            env: simulation environment.
            events: name=thing items to wait for.

        Raises:
            ValueError: if no events provided.

        Example:

        ```
        name, value = await FirstOf(env, a=q1.get(), b=q2.get())
        ```
        """
        if not events:
            raise ValueError("FirstOf requires at least one event")
        super().__init__(env)

        self._finished = False
        self._events = {}

        for key, obj in events.items():
            evt = _ensure_event(env, obj)
            self._events[key] = evt
            evt._add_waiter(lambda v, k=key, e=evt: self._child_done(k, v, e))

    def _child_done(self, key, value, winner):
        if self._finished:
            return

        self._finished = True

        for evt in self._events.values():
            if evt is not winner:
                evt.cancel()

        self.succeed((key, value))
