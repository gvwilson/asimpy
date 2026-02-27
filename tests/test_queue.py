"""Test asimpy queue."""

import pytest
from asimpy import Environment, Queue, Process


def test_queue_put_and_get():
    """Test basic put and get operations."""

    class QueueUser(Process):
        def init(self, q):
            self.q = q
            self.result = None

        async def run(self):
            await self.q.put(42)
            self.result = await self.q.get()

    env = Environment()
    q = Queue(env)
    proc = QueueUser(env, q)
    env.run()
    assert proc.result == 42


def test_queue_fifo_order():
    """Test FIFO ordering."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.q.put(1)
            await self.q.put(2)
            await self.q.put(3)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(1)
            self.results.append(await self.q.get())
            self.results.append(await self.q.get())
            self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert cons.results == [1, 2, 3]


def test_queue_blocking_get():
    """Test that get blocks when queue is empty."""

    class BlockingConsumer(Process):
        def init(self, q):
            self.q = q
            self.result = None
            self.get_time = None

        async def run(self):
            self.result = await self.q.get()
            self.get_time = self.now

    class DelayedProducer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(10)
            await self.q.put(99)

    env = Environment()
    q = Queue(env)
    cons = BlockingConsumer(env, q)
    DelayedProducer(env, q)
    env.run()
    assert cons.result == 99
    assert cons.get_time == 10


def test_queue_multiple_waiters():
    """Test multiple processes waiting on queue."""

    class Waiter(Process):
        def init(self, q, results, index):
            self.q = q
            self.results = results
            self.index = index

        async def run(self):
            value = await self.q.get()
            self.results[self.index] = value

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(1)
            await self.q.put("a")
            await self.timeout(1)
            await self.q.put("b")
            await self.timeout(1)
            await self.q.put("c")

    env = Environment()
    q = Queue(env)
    results = [None, None, None]

    Waiter(env, q, results, 0)
    Waiter(env, q, results, 1)
    Waiter(env, q, results, 2)
    Producer(env, q)

    env.run()
    assert results == ["a", "b", "c"]


def test_queue_default_unlimited_capacity():
    """Test queue with default unlimited capacity (None)."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(100):
                await self.q.put(i)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(1)
            for _ in range(100):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert len(cons.results) == 100
    assert cons.results == list(range(100))


def test_queue_max_capacity_with_waiting_getters():
    """Test that max_capacity doesn't affect direct delivery to waiting getters."""

    class Consumer(Process):
        def init(self, q, consumer_id, results_dict):
            self.q = q
            self.consumer_id = consumer_id
            self.results_dict = results_dict

        async def run(self):
            item = await self.q.get()
            self.results_dict[self.consumer_id] = item

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(1)
            for i in range(5):
                await self.q.put(i)

    env = Environment()
    q = Queue(env, max_capacity=2)
    results = {}

    for i in range(5):
        Consumer(env, q, i, results)

    Producer(env, q)
    env.run()

    assert len(results) == 5
    assert sorted(results.values()) == [0, 1, 2, 3, 4]


@pytest.mark.parametrize("max_capacity", [0, -1])
def test_queue_max_capacity_zero_invalid(max_capacity):
    """Test that invalid max_capacity raises error."""
    env = Environment()
    with pytest.raises(ValueError):
        Queue(env, max_capacity=max_capacity)


def test_queue_max_capacity_refill_after_consumption():
    """Test that queue can be refilled after items are consumed."""

    class ProducerConsumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            for i in range(3):
                await self.q.put(i)

            self.results.append(await self.q.get())

            await self.q.put(10)

            for _ in range(3):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=3)
    proc = ProducerConsumer(env, q)
    env.run()
    assert proc.results == [0, 1, 2, 10]


def test_queue_is_empty_after_get():
    """Test is_empty after consuming all items."""

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.empty_before = None
            self.empty_after = None

        async def run(self):
            await self.q.put("a")
            self.empty_before = self.q.is_empty()
            await self.q.get()
            self.empty_after = self.q.is_empty()

    env = Environment()
    q = Queue(env)
    proc = Consumer(env, q)
    env.run()
    assert proc.empty_before is False
    assert proc.empty_after is True


def test_queue_is_full():
    """Test is_full method."""

    class Filler(Process):
        def init(self, q):
            self.q = q
            self.full_states = []

        async def run(self):
            self.full_states.append(self.q.is_full())
            await self.q.put(1)
            self.full_states.append(self.q.is_full())
            await self.q.put(2)
            self.full_states.append(self.q.is_full())

    env = Environment()
    q = Queue(env, max_capacity=2)
    proc = Filler(env, q)
    env.run()
    assert proc.full_states == [False, False, True]


def test_queue_is_full_unlimited():
    """Test is_full method with unlimited capacity."""

    class Filler(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(100):
                await self.q.put(i)

    env = Environment()
    q = Queue(env)
    Filler(env, q)
    env.run()
    assert q.is_full() is False


def test_queue_put_blocks_when_full():
    """Test that put blocks when queue is at capacity."""

    class Producer(Process):
        def init(self, q):
            self.q = q
            self.put_times = []

        async def run(self):
            await self.q.put("a")
            self.put_times.append(self.now)
            await self.q.put("b")
            self.put_times.append(self.now)
            # This should block because capacity is 2
            await self.q.put("c")
            self.put_times.append(self.now)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(10)
            self.results.append(await self.q.get())
            self.results.append(await self.q.get())
            self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=2)
    prod = Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert cons.results == ["a", "b", "c"]
    # First two puts succeed immediately, third blocks until consumer gets
    assert prod.put_times[0] == 0
    assert prod.put_times[1] == 0
    assert prod.put_times[2] == 10


def test_queue_get_unblocks_putter():
    """Test that get unblocks a waiting putter and adds putter's item to queue."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.q.put(1)
            await self.q.put(2)
            # Queue is full (capacity 2). This blocks.
            await self.q.put(3)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(5)
            # Getting item 1 should unblock the putter for item 3
            self.results.append(await self.q.get())
            self.results.append(await self.q.get())
            self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=2)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert cons.results == [1, 2, 3]


def test_queue_cancel_blocked_put():
    """Test that cancelling a blocked putter's event removes it from putters."""

    class BlockedProducer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.q.put(1)  # fills queue
            await self.q.put(2)  # blocks (queue full)

    class Canceller(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(5)
            evt, _item = self.q._putters[0]
            evt.cancel()

    env = Environment()
    q = Queue(env, max_capacity=1)
    BlockedProducer(env, q)
    Canceller(env, q)
    env.run()
    assert q._putters == []


def test_queue_blocked_putters_fifo():
    """Test that multiple blocked putters are served in FIFO order."""

    class Producer(Process):
        def init(self, q, value):
            self.q = q
            self.value = value
            self.put_time = None

        async def run(self):
            await self.q.put(self.value)
            self.put_time = self.now

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(10)
            for _ in range(4):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=1)

    # First producer fills the queue
    p1 = Producer(env, q, "first")
    # These two will block
    p2 = Producer(env, q, "second")
    p3 = Producer(env, q, "third")

    cons = Consumer(env, q)
    env.run()

    # Items should come out in FIFO order: first (was in queue),
    # then second (first blocked putter), then third (second blocked putter)
    assert cons.results[:3] == ["first", "second", "third"]
    assert p1.put_time == 0
    assert p2.put_time == 10
    assert p3.put_time == 10
