import inspect
from .event import Event
from .process import Process

def ensure_event(env, obj):
    if isinstance(obj, Event):
        return obj

    if inspect.iscoroutine(obj):
        evt = Event(env)

        class Runner(Process):
            async def run(self):
                result = await obj
                evt.succeed(result)

        Runner(env)
        return evt

    raise TypeError(f"Expected Event or coroutine, got {type(obj)}")
