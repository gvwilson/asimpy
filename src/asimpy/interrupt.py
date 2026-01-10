"""Interruption exceptions."""

from typing import Any


class Interrupt(Exception):
    """Custom exception class for interruptions."""

    def __init__(self, cause: Any):
        """
        Construct a new interruption exception.

        Args:
            cause: reason for interruption.
        """
        super().__init__()
        self.cause = cause

    def __str__(self) -> str:
        """
        Format interruption as printable string.

        Returns: string representation of interruption and cause.
        """
        return f"Interrupt({self.cause})"
