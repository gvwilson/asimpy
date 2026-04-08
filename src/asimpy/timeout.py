"""Timeout event that triggers after a simulated delay."""

from .event import _CANCELLED, _PENDING, Event

# Returned by Timeout._fire() when the timeout was cancelled.
# Tells Environment.run() not to advance the clock for that phantom entry.
_NO_TIME = object()


class Timeout(Event):
    """An Event that triggers after `delay` simulated time units."""

    __slots__ = ()

    def __init__(self, env: "Environment", delay: float | int):
        if delay < 0:
            raise ValueError(f"delay must be non-negative, got {delay}")
        super().__init__(env)
        env.schedule(env.now + delay, self._fire)

    def _fire(self):
        """Trigger the timeout, or signal a phantom entry if cancelled."""
        if self._value is _CANCELLED:
            return _NO_TIME
        self.succeed()
