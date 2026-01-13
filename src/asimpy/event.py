"""Events and combinators."""


class Event:
    """Awaitable event."""

    def __init__(self, env):
        self._env = env
        self._triggered = False
        self._value = None
        self._waiters = []

    def succeed(self, value=None):
        if self._triggered:
            return
        self._triggered = True
        self._value = value
        for proc in self._waiters:
            proc._resume(value)
        self._waiters.clear()

    def _add_waiter(self, proc):
        if self._triggered:
            proc._resume(self._value)
        else:
            self._waiters.append(proc)

    def __await__(self):
        value = yield self
        return value


class Timeout(Event):
    """Timeout event for sleeping."""

    def __init__(self, env, delay):
        super().__init__(env)
        env.schedule(env.now + delay, lambda: self.succeed())


class AllOf(Event):
    """Wait for multiple events to complete."""

    def __init__(self, env, **events):
        super().__init__(env)
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
