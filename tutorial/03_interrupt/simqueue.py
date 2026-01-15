from typing import Any
from environment import Environment
from event import Event


class Queue:
    """Simple FIFO queue for simulation processes."""

    def __init__(self, env: Environment):
        self._env = env
        self._items = []
        self._getters = []

    async def get(self):
        if self._items:
            item = self._items.pop(0)
            evt = Event(self._env)
            self._env._immediate(lambda: evt.succeed(item))
            return await evt

        evt = Event(self._env)
        self._getters.append(evt)
        return await evt

    async def put(self, item: Any):
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
        else:
            self._items.append(item)
