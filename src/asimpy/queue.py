"""FIFO and priority queues."""

from abc import ABC
from .event import Event
import heapq


class BaseQueue(ABC):
    def __init__(self, env):
        self.env = env
        self._items = []
        self._getters = []

    async def get(self):
        if self._items:
            return self._items.pop(0)
        ev = Event(self.env)
        self._getters.append(ev)
        return await ev

    async def put(self, item):
        if self._getters:
            ev = self._getters.pop(0)
            ev.succeed(item)
        else:
            self._items.append(item)


class Queue(BaseQueue):
    pass


class PriorityQueue(BaseQueue):
    async def put(self, item):
        heapq.heappush(self._items, item)
        if self._getters:
            ev = self._getters.pop(0)
            ev.succeed(heapq.heappop(self._items))
