"""Wait for the first of a set of events."""

from typing import Any
from .environment import Environment
from .event import Event
from ._adapt import ensure_event


class FirstOf(Event):
    """Wait for the first of a set of events."""

    def __init__(self, env: Environment, **events: Any):
        """
        Construct new collective wait.

        Args:
            env: simulation environment.
            events: name=thing items to wait for.

        Example:

        ```
        name, value = await FirstOf(env, a=q1.get(), b=q2.get())
        ```
        """
        assert len(events) > 0
        super().__init__(env)

        self._done = False
        self._events = {}

        for key, obj in events.items():
            evt = ensure_event(env, obj)
            self._events[key] = evt
            evt._add_waiter(_FirstOfWatcher(self, key, evt))

    def _child_done(self, key, value, winner):
        if self._done:
            return
        self._done = True

        for evt in self._events.values():
            if evt is not winner:
                evt.cancel()

        self.succeed((key, value))


class _FirstOfWatcher:
    def __init__(self, parent, key, evt):
        self.parent = parent
        self.key = key
        self.evt = evt

    def _resume(self, value):
        self.parent._child_done(self.key, value, self.evt)
