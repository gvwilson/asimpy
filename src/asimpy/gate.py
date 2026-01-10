"""Gate that holds multiple processes until flagged."""

from typing import TYPE_CHECKING
from .actions import BaseAction
from .process import Process

if TYPE_CHECKING:
    from .environment import Environment


class Gate:
    """Gate that multiple processes can wait on for simultaneous release."""

    def __init__(self, env: "Environment"):
        """
        Construct a new gate.

        Args:
            env: simulation environment.
        """
        self._env = env
        self._waiting = []

    async def wait(self):
        """Wait until gate is next opened."""
        await _Wait(self)

    async def release(self):
        """Release all waiting processes."""
        await _Release(self)


# ----------------------------------------------------------------------


class _Wait(BaseAction):
    """Wait at the gate."""

    def __init__(self, gate: Gate):
        super().__init__(gate._env)
        self._gate = gate

    def act(self, proc: Process):
        self._gate._waiting.append(proc)


class _Release(BaseAction):
    """Release processes waiting at gate."""

    def __init__(self, gate: Gate):
        super().__init__(gate._env)
        self._gate = gate

    def act(self, proc: Process):
        while self._gate._waiting:
            self._env.schedule(self._env.now, self._gate._waiting.pop())
        self._env.schedule(self._env.now, proc)
