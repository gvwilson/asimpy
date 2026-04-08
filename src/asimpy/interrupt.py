"""Interrupt exception delivered to processes."""

from typing import Any


class Interrupt(Exception):
    """Exception thrown into a process by Process.interrupt()."""

    def __init__(self, cause: Any = None):
        super().__init__()
        self.cause = cause

    def __str__(self) -> str:
        return f"Interrupt({self.cause})"
