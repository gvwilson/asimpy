"""Interruption exceptions."""

class Interrupt(Exception):
    def __init__(self, cause):
        super().__init__()
        self.cause = cause

    def __str__(self):
        return f"Interrupt({self.cause})"
