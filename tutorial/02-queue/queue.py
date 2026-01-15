from typing import Any
from environment import Environment
from event import Event


class Queue:
    """
    A simple FIFO queue for discrete-event simulation.

    Processes can:
      - await queue.get() to receive an item
      - await queue.put(item) to send an item
    """

    def __init__(self, env: Environment):
        self._env = env
        self._items = []
        self._getters = []

    async def get(self):
        """
        Remove and return an item from the queue.
        If the queue is empty, wait until an item arrives.
        """
        if self._items:
            item = self._items.pop(0)
            evt = Event(self._env)
            self._env._immediate(lambda: evt.succeed(item))
            return await evt

        evt = Event(self._env)
        self._getters.append(evt)
        return await evt

    async def put(self, item: Any):
        """
        Add an item to the queue.
        If a process is waiting, resume it immediately.
        """
        if self._getters:
            evt = self._getters.pop(0)
            evt.succeed(item)
        else:
            self._items.append(item)
