"""Wait for a simulated time to pass."""

from typing import TYPE_CHECKING
from .event import Event

if TYPE_CHECKING:
    from .environment import Environment


class Timeout(Event):
    """Timeout event for sleeping."""

    def __init__(self, env: "Environment", delay: float | int):
        """
        Construct timeout.

        Args:
            env: simulation environment.
            delay: how long to wait.
        """
        assert delay >= 0
        super().__init__(env)
        env.schedule(env.now + delay, lambda: self.succeed())
