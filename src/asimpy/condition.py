"""Combination conditions."""

from .actions import BaseAction


class AllOf(BaseAction):
    def __init__(self, env, **events):
        super().__init__(env)
        self._events = events
        self._done = set()
        self._proc = None

    def act(self, proc):
        self._proc = proc
        for ev in self._events.values():
            ev._parent = self

    def notify(self, child, value=None):
        self._done.add(child)
        if len(self._done) == len(self._events):
            self._env._immediate(self._proc)
