"""Test asimpy resource."""

from asimpy import Environment, Resource, Process


def test_resource_default_capacity():
    """Test resource with default capacity."""
    env = Environment()
    res = Resource(env)
    assert res.capacity == 1


def test_resource_acquire_and_release():
    """Test basic acquire and release."""

    class ResourceUser(Process):
        def init(self, res):
            self.res = res
            self.acquired = False

        async def run(self):
            await self.res.acquire()
            self.acquired = True
            await self.res.release()

    env = Environment()
    res = Resource(env)
    proc = ResourceUser(env, res)
    env.run()
    assert proc.acquired
    assert res._count == 0


def test_resource_blocking():
    """Test that resource blocks when at capacity."""

    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire()
            await self.timeout(10)
            await self.res.release()

    class Waiter(Process):
        def init(self, res):
            self.res = res
            self.acquire_time = None

        async def run(self):
            await self.timeout(1)
            await self.res.acquire()
            self.acquire_time = self.now
            await self.res.release()

    env = Environment()
    res = Resource(env, capacity=1)
    Holder(env, res)
    waiter = Waiter(env, res)
    env.run()
    assert waiter.acquire_time == 10


def test_resource_multiple_capacity():
    """Test resource with multiple capacity."""

    class User(Process):
        def init(self, res, index, times):
            self.res = res
            self.index = index
            self.times = times

        async def run(self):
            await self.res.acquire()
            self.times[self.index] = self.now
            await self.timeout(5)
            await self.res.release()

    env = Environment()
    res = Resource(env, capacity=2)
    times = {}
    User(env, res, 1, times)
    User(env, res, 2, times)
    User(env, res, 3, times)
    env.run()
    assert times[1] == 0
    assert times[2] == 0
    assert times[3] == 5


def test_resource_context_manager():
    """Test resource as context manager."""

    class ContextUser(Process):
        def init(self, res):
            self.res = res
            self.used = False

        async def run(self):
            async with self.res:
                self.used = True

    env = Environment()
    res = Resource(env)
    proc = ContextUser(env, res)
    env.run()
    assert proc.used
    assert res._count == 0


def test_resource_cancel_available_acquire():
    """Test that cancelling an available acquire decrements count."""
    env = Environment()
    res = Resource(env, capacity=1)

    # Manually step _acquire_available to get the internal event
    coro = res._acquire_available()
    evt = coro.send(None)

    assert res._count == 1
    evt.cancel()
    assert res._count == 0


def test_resource_cancel_waiting_acquire():
    """Test that cancelling a waiting acquire removes it from waiters."""

    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire()
            await self.timeout(100)

    class BlockedAcquirer(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.timeout(1)
            await self.res.acquire()

    env = Environment()
    res = Resource(env, capacity=1)
    Holder(env, res)
    BlockedAcquirer(env, res)
    env.run(until=5)
    assert len(res._waiters) == 1
    res._waiters[0].cancel()
    assert len(res._waiters) == 0
