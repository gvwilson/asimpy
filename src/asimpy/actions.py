"""Internal actions."""


class BaseAction:
    """Base of all actions."""

    def __init__(self, env):
        self.env = env

    def __await__(self):
        yield self
        return None
