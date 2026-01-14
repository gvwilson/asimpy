"""Interrupt exceptions."""

from typing import Any


class Interrupt(Exception):
    """Interrupt raised inside a process."""

    def __init__(self, cause: Any):
        """
        Construct interruption exception.

        Args:
            cause: reason for interrupt.
        """
        super().__init__()
        self.cause = cause

    def __str__(self):
        return f"Interrupt({self.cause})"
