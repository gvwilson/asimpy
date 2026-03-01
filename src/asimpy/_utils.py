"""asimpy utilities."""

import inspect
from .event import Event
from .interrupt import Interrupt
from .process import Process


def _ensure_event(env, obj):
    """Ensure that object is an event."""
    if isinstance(obj, Event):
        return obj

    if inspect.iscoroutine(obj):
        evt = Event(env)
        runner = _Runner(env, evt, obj)
        # When the wrapper event is cancelled (e.g. by FirstOf choosing a
        # different winner), interrupt the runner so it can clean up whatever
        # primitive it is suspended inside (e.g. Queue.get removes its getter).
        evt._on_cancel = lambda: runner.interrupt("cancelled")
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
        try:
            result = await self.obj
            self.evt.succeed(result)
        except Interrupt:
            pass  # wrapper event was cancelled; obj's cleanup already ran
