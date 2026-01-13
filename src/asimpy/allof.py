from .event import Event
from ._adapt import ensure_event


class AllOf(Event):
    def __init__(self, **events):
        assert len(events) > 0

        first = next(iter(events.values()))
        if isinstance(first, Event):
            env = first._env
        else:
            raise TypeError("Cannot infer environment")

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
    """Adapter to notify parent AllOf event."""

    def __init__(self, parent, key):
        self.parent = parent
        self.key = key

    def _resume(self, value):
        self.parent._child_done(self.key, value)
