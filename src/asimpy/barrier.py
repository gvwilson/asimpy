"""Barrier that holds multiple processes until released."""

from .core import Event


class Barrier:
    """A barrier that blocks any number of processes until release() is called.

    Processes call await barrier.wait() to park.  When release() is called,
    all currently waiting processes are unblocked simultaneously.
    """

    def __init__(self, env):
        self._env = env
        self._waiters: list = []

    def wait(self) -> Event:
        """Return an Event that resolves when release() is called."""
        evt = Event(self._env)
        self._waiters.append(evt)
        return evt

    def release(self) -> None:
        """Trigger all currently waiting events."""
        for evt in self._waiters:
            evt.succeed()
        self._waiters.clear()
