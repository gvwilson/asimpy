"""Events."""

class Event:
    def __init__(self, env):
        self._env = env
        self._triggered = False
        self._cancelled = False
        self._value = None
        self._waiters = []
        self._on_cancel = None

    def succeed(self, value=None):
        if self._triggered or self._cancelled:
            return
        self._triggered = True
        self._value = value
        for proc in self._waiters:
            proc._resume(value)
        self._waiters.clear()

    def cancel(self):
        if self._triggered or self._cancelled:
            return
        self._cancelled = True
        self._waiters.clear()
        if self._on_cancel:
            self._on_cancel()

    def _add_waiter(self, proc):
        if self._triggered:
            proc._resume(self._value)
        elif not self._cancelled:
            self._waiters.append(proc)

    def __await__(self):
        value = yield self
        return value
