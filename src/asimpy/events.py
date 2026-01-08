"""Events."""


class BaseEvent:
    """Base of all events."""

    def __init__(self, env):
        self.env = env

    def __await__(self):
        yield self
        return None


class Sleep(BaseEvent):
    """Wait for a specified simulated time."""

    def __init__(self, env, delay):
        super().__init__(env)
        self.delay = delay

    def act(self, coro):
        self.env.schedule(self.env.now + self.delay, coro)


class Acquire(BaseEvent):
    """Acquire a resource."""

    def __init__(self, env, resource):
        super().__init__(env)
        self.resource = resource

    def act(self, coro):
        if self.resource.in_use < self.resource.capacity:
            self.resource.in_use += 1
            self.env.schedule(self.env.now, coro)
        else:
            self.resource.queue.append(coro)


class Release(BaseEvent):
    """Release a resource."""

    def __init__(self, env, resource):
        super().__init__(env)
        self.resource = resource

    def act(self, coro):
        self.resource.in_use -= 1
        if self.resource.queue:
            next_coro = self.resource.queue.popleft()
            self.resource.in_use += 1
            self.env.schedule(self.env.now, next_coro)
        self.env.schedule(self.env.now, coro)
