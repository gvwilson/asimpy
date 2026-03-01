"""Test asimpy barrier."""

from asimpy import Environment, Barrier, FirstOf, Process


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


# ---------------------------------------------------------------------------
# FirstOf + Barrier interaction tests
# ---------------------------------------------------------------------------


def test_firstof_barrier_wins_over_timeout():
    """FirstOf resolves on barrier.wait() when barrier is released before timeout."""

    class Waiter(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.result = None

        async def run(self):
            self.result = await FirstOf(
                self._env, b=self.barrier.wait(), t=self.timeout(10)
            )

    class Releaser(Process):
        def init(self, barrier):
            self.barrier = barrier

        async def run(self):
            await self.timeout(3)
            await self.barrier.release()

    env = Environment()
    barrier = Barrier(env)
    waiter = Waiter(env, barrier)
    Releaser(env, barrier)
    env.run()

    assert waiter.result == ("b", None)
    assert env.now == 3


def test_firstof_timeout_wins_over_barrier():
    """FirstOf resolves on timeout when barrier is never released before deadline."""

    class Waiter(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.result = None

        async def run(self):
            self.result = await FirstOf(
                self._env, b=self.barrier.wait(), t=self.timeout(5)
            )

    env = Environment()
    barrier = Barrier(env)
    waiter = Waiter(env, barrier)
    env.run()

    assert waiter.result == ("t", None)
    assert env.now == 5


def test_firstof_barrier_late_release_does_not_error():
    """Releasing a barrier after FirstOf chose a different winner must not raise.

    The barrier's internal waiter event becomes stale (its _Runner was
    interrupted), but calling release() should succeed silently.
    """

    class Waiter(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.result = None

        async def run(self):
            # Timeout fires at t=2; barrier is released at t=5.
            self.result = await FirstOf(
                self._env, b=self.barrier.wait(), t=self.timeout(2)
            )

    class LateReleaser(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.released = False

        async def run(self):
            await self.timeout(5)
            await self.barrier.release()   # must not raise
            self.released = True

    env = Environment()
    barrier = Barrier(env)
    waiter = Waiter(env, barrier)
    releaser = LateReleaser(env, barrier)
    env.run()

    assert waiter.result == ("t", None)
    assert releaser.released is True     # release() completed without error


def test_firstof_two_barriers_first_released_wins():
    """FirstOf with two barrier.wait() coroutines: the first released wins."""

    class Racer(Process):
        def init(self, b1, b2):
            self.b1 = b1
            self.b2 = b2
            self.result = None

        async def run(self):
            self.result = await FirstOf(
                self._env, b1=self.b1.wait(), b2=self.b2.wait()
            )

    class Releaser(Process):
        def init(self, b1, b2):
            self.b1 = b1
            self.b2 = b2

        async def run(self):
            await self.timeout(3)
            await self.b1.release()    # b1 fires first
            await self.timeout(2)
            await self.b2.release()    # b2 fires second (should be ignored)

    env = Environment()
    b1 = Barrier(env)
    b2 = Barrier(env)
    racer = Racer(env, b1, b2)
    Releaser(env, b1, b2)
    env.run()

    assert racer.result == ("b1", None)
    assert env.now == 5   # simulation ran to t=5 (second release)


def test_firstof_barrier_multiple_processes_some_race():
    """Some processes use FirstOf with a barrier; others wait unconditionally.

    The barrier release should reach all direct waiters, while FirstOf-wrapped
    waiters that already resolved via another event are silently ignored.
    """

    class DirectWaiter(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.done_at = None

        async def run(self):
            await self.barrier.wait()
            self.done_at = self.now

    class RacingWaiter(Process):
        def init(self, barrier):
            self.barrier = barrier
            self.result = None

        async def run(self):
            # Timeout fires at t=2; barrier released at t=5.
            self.result = await FirstOf(
                self._env, b=self.barrier.wait(), t=self.timeout(2)
            )

    class Releaser(Process):
        def init(self, barrier):
            self.barrier = barrier

        async def run(self):
            await self.timeout(5)
            await self.barrier.release()

    env = Environment()
    barrier = Barrier(env)
    direct = DirectWaiter(env, barrier)
    racer = RacingWaiter(env, barrier)
    Releaser(env, barrier)
    env.run()

    # Direct waiter sees the release at t=5.
    assert direct.done_at == 5
    # Racing waiter resolved via timeout at t=2 and is unaffected by release.
    assert racer.result == ("t", None)
