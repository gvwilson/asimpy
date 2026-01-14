"""Barrier that holds multiple processes until released."""

from typing import TYPE_CHECKING
from .event import Event

if TYPE_CHECKING:
    from .environment import Environment


class Barrier:
    """Barrier to hold multiple processes."""

    def __init__(self, env: "Environment"):
        """
        Construct barrier.

        Args:
            env: simulation environment.
        """
        self._env = env
        self._waiters = []

    async def wait(self):
        """Wait until barrier released."""
        evt = Event(self._env)
        self._waiters.append(evt)
        await evt

    async def release(self):
        """Release processes waiting at barrier."""
        for evt in self._waiters:
            evt.succeed()
        self._waiters.clear()
