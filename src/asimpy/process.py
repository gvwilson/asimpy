"""Base class for active process."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from .interrupt import Interrupt

if TYPE_CHECKING:
    from .environment import Environment


class Process(ABC):
    """Abstract base class for active process."""

    def __init__(self, env: "Environment", *args: Any, **kwargs: Any):
        """
        Construct new process.

        Args:
            env: simulation environment.
            args: extra constructor arguments passed to `init()`.
        """
        self._env = env
        self._done = False
        self._interrupt = None
        self.init(*args, **kwargs)
        self._coro = self.run()
        self._env._immediate(self._loop)

    def init(self, *args: Any, **kwargs: Any):
        """
        Extra construction after generic setup but before coroutine created.

        Args:
            args: extra constructor arguments passed to `init()`.
            kwargs: extra construct arguments passed to `init()`.
        """
        pass

    @abstractmethod
    def run(self):
        """Implementation of process behavior."""
        pass

    @property
    def now(self):
        """Shortcut to access simulation time."""
        return self._env.now

    def timeout(self, delay: int | float):
        """
        Delay this process for a specified time.

        Args:
            delay: how long to wait.
        """
        return self._env.timeout(delay)

    def interrupt(self, cause: Any):
        """
        Interrupt this process

        Args:
            cause: reason for interrupt.
        """
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
