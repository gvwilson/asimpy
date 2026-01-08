"""Events."""


class BaseEvent:
    """Base of all events."""

    def __await__(self):
        yield self
        return None


class Sleep(BaseEvent):
    """Wait for a specified simulated time."""

    def __init__(self, delay):
        super().__init__()
        self.delay = delay

    def act(self, env, coro):
        env.schedule(env.now + self.delay, coro)


class Acquire(BaseEvent):
    """Acquire a resource."""

    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    def act(self, env, coro):
        if self.resource.in_use < self.resource.capacity:
            self.resource.in_use += 1
            env.schedule(env.now, coro)
        else:
            self.resource.queue.append(coro)


class Release(BaseEvent):
    """Release a resource."""

    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    def act(self, env, coro):
        self.resource.in_use -= 1
        if self.resource.queue:
            next_coro = self.resource.queue.popleft()
            self.resource.in_use += 1
            env.schedule(env.now, next_coro)
        env.schedule(env.now, coro)
