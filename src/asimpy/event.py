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
