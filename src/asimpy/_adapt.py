import inspect
from .event import Event
from .process import Process

def ensure_event(env, obj):
    if isinstance(obj, Event):
        return obj

    if inspect.iscoroutine(obj):
        evt = Event(env)
        _Runner(env, evt, obj)
        return evt

    raise TypeError(f"Expected Event or coroutine, got {type(obj)}")



class _Runner(Process):
    def init(self, evt, obj):
        self.evt = evt
        self.obj = obj

    async def run(self):
        result = await self.obj
        self.evt.succeed(result)
