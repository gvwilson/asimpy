"""Base class for processes."""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from .interrupt import Interrupt

if TYPE_CHECKING:
    from .environment import Environment


class Process(ABC):
    """Base class for active processes."""

    def __init__(self, env: "Environment", *args: Any):
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

        self._coro = self.run()
        self.env.immediate(self)

    def init(self, *args: Any, **kwargs: Any) -> None:
        """
        Default (do-nothing) post-initialization method.

        To satisfy type-checking, derived classes must also declare `*args`
        rather than listing specific parameters by name.
        """
        pass

    def interrupt(self, cause: Any):
        """
        Interrupt this process by raising an `Interrupt` exception the
        next time the process is scheduled to run.

        Args:
            cause: reason for interrupt (attacked to `Interrupt` exception).
        """
        self._interrupt = Interrupt(cause)

    @abstractmethod
    def run(self):
        """Actions for this process."""
        pass
