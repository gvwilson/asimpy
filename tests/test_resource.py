"""Test asimpy resource."""

import pytest
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
            self.res.release()

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
            self.res.release()

    class Waiter(Process):
        def init(self, res):
            self.res = res
            self.acquire_time = None

        async def run(self):
            await self.timeout(1)
            await self.res.acquire()
            self.acquire_time = self.now
            self.res.release()

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
            self.res.release()

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
    """Pre-triggered acquire events cannot be cancelled (already done)."""
    from asimpy.event import _PENDING
    env = Environment()
    res = Resource(env, capacity=1)

    # Manually step _acquire_available to get the internal event.
    coro = res._acquire_available()
    evt = coro.send(None)

    # The event is pre-triggered; cancellation is a no-op.
    assert res._count == 1
    assert evt._value is not _PENDING  # already triggered
    evt.cancel()                       # no-op: event already resolved
    assert res._count == 1             # count unchanged — cancel had no effect


def test_resource_release_skips_cancelled_waiter():
    """release() skips cancelled waiters (lazy deletion) and serves the next valid one."""
    from asimpy.event import Event

    env = Environment()
    res = Resource(env, capacity=1)
    res._count = 1  # pretend one unit is already held

    # Place two waiter events: first cancelled, second valid.
    cancelled_evt = Event(env)
    valid_evt = Event(env)
    res._waiters.append(cancelled_evt)
    res._waiters.append(valid_evt)
    cancelled_evt.cancel()

    res.release()

    # release() must have skipped the cancelled entry and triggered the valid one.
    assert valid_evt._triggered
    # count: decremented then re-incremented for the valid waiter
    assert res._count == 1


def test_resource_cancel_waiting_acquire():
    """Cancelling a waiting acquire marks it cancelled (lazy deletion)."""
    from asimpy.event import _CANCELLED

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
    # Lazy deletion: entry remains but is marked cancelled so release() skips it.
    assert all(evt._value is _CANCELLED for evt in res._waiters)


def test_resource_rejects_non_positive_capacity():
    """Test that Resource raises ValueError for zero or negative capacity."""
    env = Environment()
    with pytest.raises(ValueError, match="capacity must be positive"):
        Resource(env, capacity=0)
    with pytest.raises(ValueError, match="capacity must be positive"):
        Resource(env, capacity=-1)
