"""Queues."""

from abc import ABC, abstractmethod
from .actions import BaseAction


class BaseQueue(ABC):
    def __init__(self, env):
        self._env = env
        self._gets = []

    async def get(self):
        return await _Get(self)

    async def put(self, obj):
        await _Put(self, obj)

    @abstractmethod
    def _dequeue(self):
        pass

    @abstractmethod
    def _empty(self):
        pass

    @abstractmethod
    def _enqueue(self, obj):
        pass


class Queue(BaseQueue):
    def __init__(self, env):
        super().__init__(env)
        self._items = []

    def _dequeue(self):
        assert len(self._items) > 0
        return self._items.pop(0)

    def _enqueue(self, obj):
        self._items.append(obj)

    def _empty(self):
        return len(self._items) == 0

    def __str__(self):
        return f"Queue({', '.join(str(i) for i in self._items)})"


# ----------------------------------------------------------------------


class _Get(BaseAction):
    def __init__(self, queue):
        super().__init__(queue._env)
        self._queue = queue
        self._proc = None
        self._item = None

    def act(self, proc):
        if self._queue._empty():
            self._proc = proc
            self._queue._gets.append(self)
        else:
            self._item = self._queue._dequeue()
            self._env.schedule(self._env.now, proc)

    def __await__(self):
        yield self
        return self._item


class _Put(BaseAction):
    def __init__(self, queue, obj):
        super().__init__(queue._env)
        self._queue = queue
        self.obj = obj

    def act(self, proc):
        self._queue._enqueue(self.obj)

        if len(self._queue._gets) > 0:
            waiting_get = self._queue._gets.pop(0)
            waiting_get._item = self._queue._dequeue()
            self._env.schedule(self._env.now, waiting_get._proc)

        self._env.schedule(self._env.now, proc)
