"""Test asimpy barrier."""

from asimpy import Environment, Barrier, Process


def test_barrier_initialization():
    """Test barrier initialization."""
    env = Environment()
    barrier = Barrier(env)
    assert len(barrier._waiters) == 0


def test_barrier_single_waiter():
    """Test barrier with single waiter."""

    class BarrierWaiter(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.released = False

        async def run(self):
            await self.barrier.wait()
            self.released = True

    class Releaser(Process):
        def init(self, barrier):
            self.barrier = barrier

        async def run(self):
            await self.timeout(5)
            await self.barrier.release()

    env = Environment()
    barrier = Barrier(env)
    waiter = BarrierWaiter(env, barrier)
    Releaser(env, barrier)
    env.run()
    assert waiter.released is True


def test_barrier_multiple_waiters():
    """Test barrier with multiple waiters."""

    class Waiter(Process):
        def init(self, barrier, results, index):
            self.barrier = barrier
            self.results = results
            self.index = index

        async def run(self):
            await self.barrier.wait()
            self.results[self.index] = self.now

    class Releaser(Process):
        def init(self, barrier):
            self.barrier = barrier

        async def run(self):
            await self.timeout(10)
            await self.barrier.release()

    env = Environment()
    barrier = Barrier(env)
    results = {}

    Waiter(env, barrier, results, 1)
    Waiter(env, barrier, results, 2)
    Waiter(env, barrier, results, 3)
    Releaser(env, barrier)

    env.run()
    assert results[1] == 10
    assert results[2] == 10
    assert results[3] == 10
