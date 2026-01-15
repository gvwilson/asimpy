from typing import Any


class Interrupt(Exception):
    """Exception raised inside a process when it is interrupted."""

    def __init__(self, cause: Any):
        super().__init__()
        self.cause = cause

    def __str__(self):
        return f"Interrupt({self.cause})"
