"""Gate that holds multiple processes until flagged."""

from .actions import BaseAction


class Gate:
    """Gate that multiple processes can wait on for simultaneous release."""

    def __init__(self, env):
        """
        Construct a new gate.

        Args:
            env: simulation environment.
        """
        self.env = env
        self.pending = []

    async def wait(self):
        """Wait until gate is next opened."""

        await _Wait(self)

    async def release(self):
        """Release all waiting processes."""

        await _Release(self)


# ----------------------------------------------------------------------


class _Wait(BaseAction):
    """Wait at the gate."""

    def __init__(self, gate):
        super().__init__(gate.env)
        self.gate = gate

    def act(self, coro):
        self.gate.pending.append(coro)


class _Release(BaseAction):
    """Release processes waiting at gate."""

    def __init__(self, gate):
        super().__init__(gate.env)
        self.gate = gate

    def act(self, coro):
        while self.gate.pending:
            self.env.schedule(self.env.now, self.gate.pending.pop())
        self.env.schedule(self.env.now, coro)
