"""Base class for processes."""

from .interrupt import Interrupt


class Process:
    def __init__(self, env, *args):
        self.env = env
        self._interrupt = None
        self.init(*args)
        self.coro = self.run()
        self.env.start(self)

    def init(self, *args):
        pass

    def interrupt(self, cause):
        self._interrupt = Interrupt(cause)
