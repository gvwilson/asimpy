"""Wait for all events in a set to complete."""

from typing import Any
from .environment import Environment
from .event import Event
from ._adapt import ensure_event


class AllOf(Event):
    """Wait for all of a set of events."""
    
    def __init__(self, env: Environment, **events: Any):
        """
        Construct new collective wait.

        Args:
            env: simulation environment.
            events: name=thing items to wait for.

        Example:

        ```
        name, value = await AllOf(env, a=q1.get(), b=q2.get())
        ```
        """
        assert len(events) > 0
        super().__init__(env)

        self._events = {}
        self._results = {}

        for key, obj in events.items():
            evt = ensure_event(env, obj)
            self._events[key] = evt
            evt._add_waiter(_AllOfWatcher(self, key))


    def _child_done(self, key, value):
        self._results[key] = value
        if len(self._results) == len(self._events):
            self.succeed(self._results)


class _AllOfWatcher:
    def __init__(self, parent, key):
        self.parent = parent
        self.key = key

    def _resume(self, value):
        self.parent._child_done(self.key, value)
