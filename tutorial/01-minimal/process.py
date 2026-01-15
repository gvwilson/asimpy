from abc import ABC, abstractmethod
from environment import Environment


class Process(ABC):
    """Base class for active simulation processes."""

    def __init__(self, env: Environment):
        self._env = env
        self._done = False
        self._coro = self.run()
        self._env._immediate(self._step)

    @abstractmethod
    async def run(self):
        pass

    @property
    def now(self):
        return self._env.now

    def timeout(self, delay: float | int):
        return self._env.timeout(delay)

    def _step(self, value=None):
        if self._done:
            return
        try:
            evt = self._coro.send(value)
            evt._add_waiter(self)
        except StopIteration:
            self._done = True

    def _resume(self, value=None):
        self._env._immediate(lambda: self._step(value))
