"""Gate that holds multiple processes until released."""

from .event import Event


class Gate:
    def __init__(self, env):
        self.env = env
        self._waiters = []

    async def wait(self):
        ev = Event(self.env)
        self._waiters.append(ev)
        await ev

    async def release(self):
        for ev in self._waiters:
            ev.succeed()
        self._waiters.clear()
