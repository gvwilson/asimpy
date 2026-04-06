"""Tests for active_process and PreemptiveResource."""

import pytest
from asimpy import Environment, Interrupt, Process
from asimpy import Preempted, PreemptiveResource


def test_active_process_is_none_initially():
    env = Environment()
    assert env._active_process is None


def test_active_process_set_during_run():
    """active_process equals the running process inside run()."""

    class Checker(Process):
        def init(self):
            self.seen = None

        async def run(self):
            self.seen = self._env._active_process

    env = Environment()
    proc = Checker(env)
    env.run()
    assert proc.seen is proc


def test_active_process_cleared_after_run():
    """active_process is None after simulation completes."""

    class Noop(Process):
        async def run(self):
            pass

    env = Environment()
    Noop(env)
    env.run()
    assert env._active_process is None


def test_active_process_identifies_correct_process():
    """active_process is the process that is currently executing."""

    class Recorder(Process):
        def init(self, records, delay):
            self.records = records
            self.delay = delay

        async def run(self):
            await self.timeout(self.delay)
            self.records.append(self._env._active_process)

    env = Environment()
    records = []
    p1 = Recorder(env, records, 1)
    p2 = Recorder(env, records, 2)
    env.run()
    assert records == [p1, p2]


def test_invalid_capacity_zero():
    env = Environment()
    with pytest.raises(ValueError, match="capacity must be positive"):
        PreemptiveResource(env, capacity=0)


def test_invalid_capacity_negative():
    env = Environment()
    with pytest.raises(ValueError, match="capacity must be positive"):
        PreemptiveResource(env, capacity=-1)


def test_default_capacity_is_one():
    env = Environment()
    res = PreemptiveResource(env)
    assert res.capacity == 1


def test_basic_acquire_and_release():
    class Worker(Process):
        def init(self, res):
            self.res = res
            self.done = False

        async def run(self):
            await self.res.acquire()
            await self.timeout(5)
            self.res.release()
            self.done = True

    env = Environment()
    res = PreemptiveResource(env)
    w = Worker(env, res)
    env.run()
    assert w.done
    assert res.count == 0


def test_count_reflects_users():
    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire()
            await self.timeout(10)

    env = Environment()
    res = PreemptiveResource(env, capacity=2)
    Holder(env, res)
    Holder(env, res)
    env.run(until=1)
    assert res.count == 2


def test_waiter_is_served_when_holder_releases():
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
            await self.res.acquire(preempt=False)
            self.acquire_time = self.now
            self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Holder(env, res)
    w = Waiter(env, res)
    env.run()
    assert w.acquire_time == 10


def test_release_raises_if_not_user():
    """release() raises RuntimeError when the process does not hold the resource."""

    class Releaser(Process):
        def init(self, res):
            self.res = res
            self.error = None

        async def run(self):
            try:
                self.res.release()
            except RuntimeError as exc:
                self.error = exc

    env = Environment()
    res = PreemptiveResource(env)
    r = Releaser(env, res)
    env.run()
    assert r.error is not None


def _make_preemptable_worker(priority, service_time):
    """Returns a Process class that handles Preempted and re-acquires."""

    class Worker(Process):
        def init(self, res):
            self.res = res
            self.preempted = False
            self.done = False

        async def run(self):
            remaining = service_time
            while remaining > 0:
                await self.res.acquire(priority=priority)
                try:
                    await self.timeout(remaining)
                    remaining = 0
                    self.res.release()
                    self.done = True
                except Interrupt as intr:
                    if isinstance(intr.cause, Preempted):
                        remaining -= self.now - intr.cause.usage_since
                        self.preempted = True
                        # do NOT call release() — preemptor already removed us
                    else:
                        self.res.release()
                        raise

    return Worker


def test_preemption_occurs():
    """A higher-priority process preempts a lower-priority user."""
    LowWorker = _make_preemptable_worker(priority=2, service_time=10)

    class HighWorker(Process):
        def init(self, res):
            self.res = res
            self.done = False

        async def run(self):
            await self.timeout(3)
            await self.res.acquire(priority=1)
            await self.timeout(4)
            self.res.release()
            self.done = True

    env = Environment()
    res = PreemptiveResource(env)
    low = LowWorker(env, res)
    high = HighWorker(env, res)
    env.run()

    assert low.preempted
    assert low.done
    assert high.done
    assert res.count == 0


def test_preemption_completes_at_correct_time():
    """Timeline: low starts at 0, preempted at 3, high finishes at 7, low finishes at 14."""

    class HighWorker(Process):
        def init(self, res):
            self.res = res
            self.finish_time = None

        async def run(self):
            await self.timeout(3)
            await self.res.acquire(priority=1)
            await self.timeout(4)
            self.res.release()
            self.finish_time = self.now

    class TrackingLow(Process):
        def init(self, res):
            self.res = res
            self.finish_time = None

        async def run(self):
            remaining = 10
            while remaining > 0:
                await self.res.acquire(priority=2)
                try:
                    await self.timeout(remaining)
                    remaining = 0
                    self.res.release()
                    self.finish_time = self.now
                except Interrupt as intr:
                    if isinstance(intr.cause, Preempted):
                        remaining -= self.now - intr.cause.usage_since

    env = Environment()
    res = PreemptiveResource(env)
    low = TrackingLow(env, res)
    high = HighWorker(env, res)
    env.run()

    assert high.finish_time == 7
    assert low.finish_time == 14


def test_preempted_cause_fields():
    """Preempted.by is the preemptor; usage_since is when the victim acquired."""

    class LowWorker(Process):
        def init(self, res):
            self.res = res
            self.cause = None

        async def run(self):
            await self.res.acquire(priority=2)
            try:
                await self.timeout(10)
            except Interrupt as intr:
                if isinstance(intr.cause, Preempted):
                    self.cause = intr.cause

    class HighWorker(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.timeout(5)
            await self.res.acquire(priority=1)
            self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    low = LowWorker(env, res)
    high = HighWorker(env, res)
    env.run()

    assert low.cause is not None
    assert low.cause.by is high
    assert low.cause.usage_since == 0


def test_no_preemption_when_preempt_false():
    """acquire(preempt=False) waits even if it has higher priority."""

    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire(priority=5)
            await self.timeout(10)
            self.res.release()

    class HighWaiter(Process):
        def init(self, res):
            self.res = res
            self.acquire_time = None

        async def run(self):
            await self.timeout(2)
            await self.res.acquire(priority=0, preempt=False)
            self.acquire_time = self.now
            self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Holder(env, res)
    hw = HighWaiter(env, res)
    env.run()
    assert hw.acquire_time == 10


def test_no_preemption_when_equal_priority():
    """A request at the same priority as the current user does not preempt."""

    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire(priority=1)
            await self.timeout(10)
            self.res.release()

    class Requester(Process):
        def init(self, res):
            self.res = res
            self.acquire_time = None

        async def run(self):
            await self.timeout(3)
            await self.res.acquire(priority=1)
            self.acquire_time = self.now
            self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Holder(env, res)
    req = Requester(env, res)
    env.run()
    assert req.acquire_time == 10


def test_waiters_served_in_priority_order():
    """Multiple waiters are woken in priority order, not arrival order."""

    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire(priority=9)
            await self.timeout(5)
            self.res.release()

    class Waiter(Process):
        def init(self, res, priority, order_list):
            self.res = res
            self.priority = priority
            self.order_list = order_list

        async def run(self):
            await self.timeout(1)
            await self.res.acquire(priority=self.priority, preempt=False)
            self.order_list.append(self.priority)
            await self.timeout(1)
            self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Holder(env, res)
    order = []
    Waiter(env, res, 3, order)
    Waiter(env, res, 1, order)
    Waiter(env, res, 2, order)
    env.run()
    assert order == [1, 2, 3]


def test_preemption_with_capacity_two():
    """Preemption evicts only the worst-priority user when capacity > 1."""
    LowWorker3 = _make_preemptable_worker(priority=3, service_time=10)
    LowWorker2 = _make_preemptable_worker(priority=2, service_time=10)

    class HighArrival(Process):
        def init(self, res):
            self.res = res
            self.done = False

        async def run(self):
            await self.timeout(2)
            await self.res.acquire(priority=1)
            await self.timeout(3)
            self.res.release()
            self.done = True

    env = Environment()
    res = PreemptiveResource(env, capacity=2)
    w3 = LowWorker3(env, res)
    w2 = LowWorker2(env, res)
    ha = HighArrival(env, res)
    env.run()

    assert w3.preempted  # priority=3 is the worst, gets evicted
    assert not w2.preempted  # priority=2 survives
    assert ha.done


def test_non_preempted_interrupt_reraises():
    """_make_preemptable_worker re-raises non-Preempted interrupts after releasing."""
    Worker = _make_preemptable_worker(priority=0, service_time=20)

    class Interruptor(Process):
        def init(self, target):
            self.target = target

        async def run(self):
            await self.timeout(3)
            self.target.interrupt("oops")

    env = Environment()
    res = PreemptiveResource(env)
    w = Worker(env, res)
    Interruptor(env, w)

    with pytest.raises(Interrupt):
        env.run()

    assert res.count == 0


def test_release_skips_cancelled_waiter():
    """release() skips cancelled waiters and serves the next valid one."""

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
            self.acquired = False

        async def run(self):
            await self.timeout(1)
            await self.res.acquire(preempt=False)
            self.acquired = True
            self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Holder(env, res)
    # Two waiters; cancel the first one's event directly after they park.
    w1 = Waiter(env, res)
    w2 = Waiter(env, res)
    env.run(until=2)

    # Both waiters are now parked; cancel the first one's event.
    res._waiters[0][3].cancel()

    env.run()  # continue to completion
    assert not w1.acquired  # cancelled waiter never got the resource
    assert w2.acquired
