from .event import Event
from ._adapt import ensure_event


class FirstOf(Event):
    def __init__(self, env, **awaitables):
        assert awaitables

        super().__init__(env)

        self._done = False
        self._events = {}

        for key, obj in awaitables.items():
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
