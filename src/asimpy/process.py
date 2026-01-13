"""Base class for active processes with interrupt support."""

from abc import ABC, abstractmethod
from .interrupt import Interrupt


class Process(ABC):
    def __init__(self, env, *args):
        self._env = env
        self.init(*args)
        self._done = False
        self._interrupt = None
        self._coro = self.run()
        self._env._immediate(self._loop)

    def init(self, *args, **kwargs):
        pass

    @property
    def env(self):
        return self._env

    @property
    def now(self):
        return self._env.now

    def timeout(self, delay):
        return self._env.timeout(delay)

    @abstractmethod
    def run(self):
        pass

    def interrupt(self, cause):
        if not self._done:
            self._interrupt = Interrupt(cause)
            self._env._immediate(self._loop)

    def _loop(self, value=None):
        if self._done:
            return

        try:
            if self._interrupt is None:
                yielded = self._coro.send(value)
            else:
                exc = self._interrupt
                self._interrupt = None
                yielded = self._coro.throw(exc)
            yielded._add_waiter(self)

        except StopIteration:
            self._done = True

        except Exception as exc:
            self._done = True
            raise exc

    def _resume(self, value=None):
        if not self._done:
            self._env._immediate(lambda: self._loop(value))
