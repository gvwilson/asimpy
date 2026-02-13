"""asimpy utilities."""

import inspect
from .event import Event
from .process import Process


def _ensure_event(env, obj):
    """Ensure that object is an event."""
    if isinstance(obj, Event):
        return obj

    if inspect.iscoroutine(obj):
        evt = Event(env)
        _Runner(env, evt, obj)
        return evt

    raise TypeError(f"Expected Event or coroutine, got {type(obj)}")


def _validate(cond, msg):
    """Check value during construction and raise ValueError if invalid."""
    if not cond:
        raise ValueError(msg)


class _Runner(Process):
    def init(self, evt, obj):
        self.evt = evt
        self.obj = obj

    async def run(self):
        result = await self.obj
        self.evt.succeed(result)
