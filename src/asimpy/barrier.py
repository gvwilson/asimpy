"""Barrier that holds multiple processes until released."""

from .event import Event


class Barrier:
    def __init__(self, env):
        self._env = env
        self._waiters = []

    async def wait(self):
        evt = Event(self._env)
        self._waiters.append(evt)
        await evt

    async def release(self):
        for evt in self._waiters:
            evt.succeed()
        self._waiters.clear()
