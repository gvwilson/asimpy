"""Awaitable actions."""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .environment import Environment


class BaseAction:
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

    def __await__(self) -> Any:
        """Handle `await`."""
        yield self
        return None
