"""Awaitable actions."""

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .environment import Environment
    from .process import Process


class BaseAction(ABC):
    """
    Base of all internal awaitable actions. Simulation authors should not use this directly.
    """

    def __init__(self, env: "Environment"):
        """
        Construct a new awaitable action.

        Args:
            env: simulation environment.
        """
        self._env = env
        self._parent = None
        self._cancelled = False

    def __await__(self) -> Any:
        """Handle `await`."""
        yield self
        return None

    def _action(self, proc: "Process"):
        """Perform generic action then class-specific action."""
        if self._cancelled:
            return
        return self.act(proc)

    @abstractmethod
    def act(self, proc: "Process"):
        """Perform class-specific action."""
        pass
