"""Base class for processes."""

from .interrupt import Interrupt


class Process:
    """Base class for active processes."""

    def __init__(self, env, *args):
        """
        Construct a new process by performing common initialization,
        calling the user-defined `init()` method (no underscores),
        and registering the coroutine created by the `run()` method
        with the environment.

        Args:
            env: simulation environment.
            *args: to be passed to `init()` for custom initialization.
        """
        self.env = env
        self._interrupt = None
        self.init(*args)
        self.coro = self.run()
        self.env.start(self)

    def init(self, *args):
        """Default do-nothing custom initialization method."""

        pass

    def interrupt(self, cause):
        """
        Interrupt this process by raising an `Interrupt` exception the
        next time the process is scheduled to run.

        Args:
            cause: reason for interrupt (attacked to `Interrupt` exception).
        """
        self._interrupt = Interrupt(cause)
