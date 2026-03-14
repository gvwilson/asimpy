"""Test asimpy FirstOf."""

import pytest
from asimpy import Environment, Event, FirstOf, Process, Queue, Timeout


def test_firstof_single_event():
    """Test FirstOf with single event."""

    class FirstOfUser(Process):
        def init(self):
            self.result = ()

        async def run(self):
            self.result = await FirstOf(self._env, a=self.timeout(5))

    env = Environment()
    proc = FirstOfUser(env)
    env.run()
    assert proc.result == ("a", None)


def test_firstof_multiple_events_first_wins():
    """Test FirstOf returns first completed event."""

    class MultiFirstOf(Process):
        def init(self):
            self.result = ()

        async def run(self):
            self.result = await FirstOf(
                self._env, fast=self.timeout(3), slow=self.timeout(10)
            )

    env = Environment()
    proc = MultiFirstOf(env)
    env.run()
    assert proc.result == ("fast", None)
    assert env.now == 3


def test_firstof_cancels_others():
    """Test FirstOf cancels other events."""

    class CancelTest(Process):
        def init(self):
            self.result = None
            self.timeout1 = Timeout(self._env, 5)
            self.timeout2 = Timeout(self._env, 10)

        async def run(self):
            self.result = await FirstOf(self._env, a=self.timeout1, b=self.timeout2)

    env = Environment()
    proc = CancelTest(env)
    env.run()
    assert proc.timeout2._cancelled is True


def test_firstof_already_triggered_events():
    """Test FirstOf with events that are already triggered hits early return."""
    env = Environment()
    evt_a = Event(env)
    evt_b = Event(env)
    evt_a.succeed("first")
    evt_b.succeed("second")

    class Waiter(Process):
        def init(self, evt_a, evt_b):
            self.evt_a = evt_a
            self.evt_b = evt_b
            self.result = None

        async def run(self):
            self.result = await FirstOf(self._env, a=self.evt_a, b=self.evt_b)

    proc = Waiter(env, evt_a, evt_b)
    env.run()
    assert proc.result == ("a", "first")


# ---------------------------------------------------------------------------
# Bug-fix tests: FirstOf with Queue.get() coroutines must not lose items
# ---------------------------------------------------------------------------


def test_firstof_queue_loser_item_preserved_empty_queues():
    """Item put into the losing queue after FirstOf resolves must not be lost.

    This is the exact scenario from the bug report: both queues are empty when
    FirstOf is set up, q1 wins, then something is put into q2.  Before the fix,
    q2's item was silently consumed by the orphaned _Runner getter.
    """

    class Consumer(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2
            self.got = None

        async def run(self):
            self.got = await FirstOf(self._env, a=self.q1.get(), b=self.q2.get())

    class Producer(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2

        async def run(self):
            await self.timeout(1)
            await self.q1.put("from_q1")  # q1 wins
            await self.timeout(1)
            await self.q2.put("from_q2")  # must remain in q2

    env = Environment()
    q1 = Queue(env)
    q2 = Queue(env)
    consumer = Consumer(env, q1, q2)
    Producer(env, q1, q2)
    env.run(until=10)

    assert consumer.got == ("a", "from_q1")
    assert list(q2._items) == ["from_q2"], (
        "item_from_q2 was silently consumed by the orphaned _Runner getter"
    )


def test_firstof_queue_loser_item_preserved_nonempty_queues():
    """Winner's item is returned; loser's pre-loaded item must not be lost.

    Both queues already contain an item when FirstOf is set up.  The winner
    (a) is the queue whose _Runner fires first.  The loser's item must survive.
    """

    class Racer(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2
            self.got: tuple[str, object] = ("", None)

        async def run(self):
            # Both queues already have items at this point.
            self.got = await FirstOf(self._env, a=self.q1.get(), b=self.q2.get())

    env = Environment()
    q1 = Queue(env)
    q2 = Queue(env)

    # Pre-load both queues before the Racer starts.
    env.immediate(lambda: q1._items.append("alpha"))
    env.immediate(lambda: q2._items.append("beta"))

    racer = Racer(env, q1, q2)
    env.run()

    # Queue a's _Runner is created first, so it always wins.
    winner_name, winner_value = racer.got
    assert winner_name == "a"
    assert winner_value == "alpha"
    assert list(q2._items) == ["beta"], "loser queue item was silently lost"


def test_firstof_queue_loser_getter_removed():
    """After FirstOf resolves, the losing queue's orphan getter must be cancelled.

    Lazy deletion leaves cancelled entries in _getters, but put() must skip them
    so that a subsequent put() delivers its item to a real waiter, not a ghost.
    """
    from asimpy.event import _CANCELLED

    class Consumer(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2

        async def run(self):
            await FirstOf(self._env, a=self.q1.get(), b=self.q2.get())

    class Trigger(Process):
        def init(self, q1):
            self.q1 = q1

        async def run(self):
            await self.timeout(1)
            await self.q1.put("go")

    env = Environment()
    q1 = Queue(env)
    q2 = Queue(env)
    Consumer(env, q1, q2)
    Trigger(env, q1)
    env.run(until=5)

    # With lazy deletion, cancelled getters remain in the deque but are marked
    # cancelled so that put() skips them rather than silently losing the item.
    assert all(
        evt._value is _CANCELLED for evt in q2._getters
    ), "non-cancelled getter remained in q2._getters after FirstOf"


def test_firstof_queue_loser_can_still_be_gotten():
    """A separate process can still get() from the losing queue after FirstOf."""

    class Consumer(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2
            self.firstof_result = None

        async def run(self):
            self.firstof_result = await FirstOf(
                self._env, a=self.q1.get(), b=self.q2.get()
            )

    class LateGetter(Process):
        def init(self, q2):
            self.q2 = q2
            self.got = None

        async def run(self):
            await self.timeout(3)
            self.got = await self.q2.get()

    class Producer(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2

        async def run(self):
            await self.timeout(1)
            await self.q1.put("wins")
            await self.timeout(1)
            await self.q2.put("for_late_getter")

    env = Environment()
    q1 = Queue(env)
    q2 = Queue(env)
    consumer = Consumer(env, q1, q2)
    late = LateGetter(env, q2)
    Producer(env, q1, q2)
    env.run(until=10)

    assert consumer.firstof_result == ("a", "wins")
    assert late.got == "for_late_getter"


def test_firstof_queue_multiple_rounds():
    """FirstOf can be used repeatedly on the same queues without leaking state."""

    class RoundRobin(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2
            self.results = []

        async def run(self):
            for _ in range(3):
                name, value = await FirstOf(self._env, a=self.q1.get(), b=self.q2.get())
                self.results.append((name, value))

    class Feeder(Process):
        def init(self, q1, q2):
            self.q1 = q1
            self.q2 = q2

        async def run(self):
            for t, q, v in [(1, "q1", "x"), (2, "q2", "y"), (3, "q1", "z")]:
                await self.timeout(t)
                await (self.q1 if q == "q1" else self.q2).put(v)

    env = Environment()
    q1 = Queue(env)
    q2 = Queue(env)
    rr = RoundRobin(env, q1, q2)
    Feeder(env, q1, q2)
    env.run(until=20)

    from asimpy.event import _CANCELLED
    assert rr.results == [("a", "x"), ("b", "y"), ("a", "z")]
    # Lazy deletion: any residual entries must be cancelled (harmless).
    assert all(evt._value is _CANCELLED for evt in q1._getters)
    assert all(evt._value is _CANCELLED for evt in q2._getters)


def test_firstof_requires_at_least_one_event():
    """Test that FirstOf raises ValueError when given no events."""
    env = Environment()
    with pytest.raises(ValueError, match="at least one event"):
        FirstOf(env)
