from .event import Event

class FirstOf(Event):
    """Wait until the first of the given events completes."""

    def __init__(self, **events):
        assert len(events) > 0

        first_evt = next(iter(events.values()))
        env = first_evt._env
        super().__init__(env)

        self._events = events
        self._done = False

        for key, evt in events.items():
            evt._add_waiter(_FirstOfWatcher(self, key))

    def _child_done(self, key, value):
        if self._done:
            return
        self._done = True
        self.succeed((key, value))


class _FirstOfWatcher:
    """Adapter to notify parent FirstOf event."""

    def __init__(self, parent: FirstOf, key: str):
        self.parent = parent
        self.key = key

    def _resume(self, value):
        self.parent._child_done(self.key, value)
