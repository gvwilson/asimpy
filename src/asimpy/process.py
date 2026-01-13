"""Base class for active processes with interrupt support."""

from abc import ABC, abstractmethod
from .interrupt import Interrupt


class Process(ABC):
    def __init__(self, env, *args):
        self.env = env
        self.init(*args)
        self._coro = self.run()
        self._interrupt = None
        self._done = False
        self.env.immediate(self._step_loop)

    def init(self, *args, **kwargs):
        pass

    @abstractmethod
    def run(self):
        pass

    def _step_loop(self, value=None):
        if self._done:
            return  # already finished

        try:
            if self._interrupt is not None:
                exc = self._interrupt
                self._interrupt = None
                yielded = self._coro.throw(exc)
            else:
                yielded = self._coro.send(value)
            # Schedule next resume when the awaited event is ready
            yielded._add_waiter(self)
        except StopIteration:
            self._done = True  # mark coroutine as finished
        except Exception:
            self._done = True
            raise

    def _resume(self, value=None):
        if not self._done:
            self.env.immediate(lambda: self._step_loop(value))

    def interrupt(self, cause):
        if not self._done:
            self._interrupt = Interrupt(cause)
            self.env.immediate(self._step_loop)
