from .event import Event


class AllOf(Event):
    """Wait for multiple events to complete."""

    def __init__(self, **events):
        assert len(events) > 0
        first_evt = next(iter(events.values()))
        super().__init__(first_evt._env)

        self._events = events
        self._results = {}
        for key, evt in events.items():
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
