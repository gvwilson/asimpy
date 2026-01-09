"""Awaitable actions."""


class BaseAction:
    """
    Base of all internal awaitable actions. Simulation authors should not use this directly.
    """

    def __init__(self, env):
        """
        Construct a new awaitable action.

        Args:
            env: simulation environment.
        """

        self.env = env

    def __await__(self):
        """Handle `await`."""

        yield self
        return None
