from typing import Any
from abc import ABC, abstractmethod
from environment import Environment
from interrupt import Interrupt


class Process(ABC):
    """Base class for active simulation processes."""

    def __init__(self, env: Environment):
        self._env = env
        self._done = False
        self._interrupt = None
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

    def interrupt(self, cause: Any):
        """
        Interrupt this process.

        The interrupt is delivered as an exception at the next
        suspension point.
        """
        if not self._done:
            self._interrupt = Interrupt(cause)
            self._env._immediate(self._step)

    def _step(self, value=None):
        if self._done:
            return

        try:
            if self._interrupt is None:
                evt = self._coro.send(value)
            else:
                exc = self._interrupt
                self._interrupt = None
                evt = self._coro.throw(exc)

            evt._add_waiter(self)

        except StopIteration:
            self._done = True

    def _resume(self, value=None):
        self._env._immediate(lambda: self._step(value))
