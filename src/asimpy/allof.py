"""Wait for all events in a set to complete."""

from typing import Any
from .environment import Environment
from .event import Event
from ._utils import _ensure_event


class AllOf(Event):
    """Wait for all of a set of events."""

    __slots__ = ("_events", "_results")

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
        name, value = await AllOf(env, a=q1.get(), b=q2.get())
        ```
        """
        if not events:
            raise ValueError("AllOf requires at least one event")
        super().__init__(env)

        self._events = {}
        self._results = {}

        for key, obj in events.items():
            evt = _ensure_event(env, obj)
            self._events[key] = evt
            evt._add_waiter(lambda v, k=key: self._child_done(k, v))

    def _child_done(self, key, value):
        self._results[key] = value
        if len(self._results) == len(self._events):
            self.succeed(self._results)
