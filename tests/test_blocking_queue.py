"""Test asimpy BlockingQueue."""

import pytest
from asimpy import Environment, BlockingQueue, Process


def test_blocking_queue_initialization():
    """Test BlockingQueue construction with valid capacity."""
    env = Environment()
    bq = BlockingQueue(env, max_capacity=5)
    assert bq._max_capacity == 5
    assert bq._items == []
    assert bq._getters == []
    assert bq._putters == []


@pytest.mark.parametrize("max_capacity", [0, -3])
def test_blocking_queue_invalid_max_capacity(max_capacity):
    """Test that invalid max_capacity raises error."""
    env = Environment()
    with pytest.raises(ValueError):
        BlockingQueue(env, max_capacity=max_capacity)


def test_blocking_queue_is_empty():
    """Test is_empty method."""
    env = Environment()
    bq = BlockingQueue(env, max_capacity=3)
    assert bq.is_empty() is True
    bq._items.append(1)
    assert bq.is_empty() is False
    bq._items.append(2)
    assert bq.is_empty() is False


def test_blocking_queue_is_empty_after_get():
    """Test is_empty after consuming all items."""

    class Consumer(Process):
        def init(self, bq):
            self.bq = bq
            self.empty_before = None
            self.empty_after = None

        async def run(self):
            await self.bq.put("a")
            self.empty_before = self.bq.is_empty()
            await self.bq.get()
            self.empty_after = self.bq.is_empty()

    env = Environment()
    bq = BlockingQueue(env, max_capacity=3)
    proc = Consumer(env, bq)
    env.run()
    assert proc.empty_before is False
    assert proc.empty_after is True


def test_blocking_queue_is_full():
    """Test is_full method."""
    env = Environment()
    bq = BlockingQueue(env, max_capacity=2)
    assert bq.is_full() is False
    bq._items.append(1)
    assert bq.is_full() is False
    bq._items.append(2)
    assert bq.is_full() is True


def test_blocking_queue_put_not_full():
    """Test put when queue is not full adds item directly."""

    class PutUser(Process):
        def init(self, bq):
            self.bq = bq
            self.result = None

        async def run(self):
            self.result = await self.bq.put("hello")

    env = Environment()
    bq = BlockingQueue(env, max_capacity=3)
    proc = PutUser(env, bq)
    env.run()
    assert proc.result is True
    assert bq._items == ["hello"]


def test_blocking_queue_get_with_items():
    """Test get when queue has items."""

    class GetUser(Process):
        def init(self, bq):
            self.bq = bq
            self.result = None

        async def run(self):
            await self.bq.put(42)
            self.result = await self.bq.get()

    env = Environment()
    bq = BlockingQueue(env, max_capacity=3)
    proc = GetUser(env, bq)
    env.run()
    assert proc.result == 42
    assert bq._items == []


def test_blocking_queue_get_empty_blocks():
    """Test that get blocks when queue is empty until put delivers."""

    class Consumer(Process):
        def init(self, bq):
            self.bq = bq
            self.result = None
            self.get_time = None

        async def run(self):
            self.result = await self.bq.get()
            self.get_time = self.now

    class Producer(Process):
        def init(self, bq):
            self.bq = bq

        async def run(self):
            await self.timeout(5)
            await self.bq.put(99)

    env = Environment()
    bq = BlockingQueue(env, max_capacity=3)
    cons = Consumer(env, bq)
    Producer(env, bq)
    env.run()
    assert cons.result == 99
    assert cons.get_time == 5


def test_blocking_queue_put_to_waiting_getter():
    """Test that put delivers directly to a waiting getter."""

    class Consumer(Process):
        def init(self, bq):
            self.bq = bq
            self.result = None

        async def run(self):
            self.result = await self.bq.get()

    class Producer(Process):
        def init(self, bq):
            self.bq = bq
            self.put_result = None

        async def run(self):
            await self.timeout(1)
            self.put_result = await self.bq.put("direct")

    env = Environment()
    bq = BlockingQueue(env, max_capacity=1)
    cons = Consumer(env, bq)
    prod = Producer(env, bq)
    env.run()
    assert cons.result == "direct"
    assert prod.put_result is True
    assert bq._items == []


def test_blocking_queue_put_blocks_when_full():
    """Test that put blocks when queue is at capacity."""

    class Producer(Process):
        def init(self, bq):
            self.bq = bq
            self.put_times = []

        async def run(self):
            await self.bq.put("a")
            self.put_times.append(self.now)
            await self.bq.put("b")
            self.put_times.append(self.now)
            # This should block because capacity is 2
            await self.bq.put("c")
            self.put_times.append(self.now)

    class Consumer(Process):
        def init(self, bq):
            self.bq = bq
            self.results = []

        async def run(self):
            await self.timeout(10)
            self.results.append(await self.bq.get())
            self.results.append(await self.bq.get())
            self.results.append(await self.bq.get())

    env = Environment()
    bq = BlockingQueue(env, max_capacity=2)
    prod = Producer(env, bq)
    cons = Consumer(env, bq)
    env.run()
    assert cons.results == ["a", "b", "c"]
    # First two puts succeed immediately, third blocks until consumer gets
    assert prod.put_times[0] == 0
    assert prod.put_times[1] == 0
    assert prod.put_times[2] == 10


def test_blocking_queue_get_unblocks_putter():
    """Test that get unblocks a waiting putter and adds putter's item to queue."""

    class Producer(Process):
        def init(self, bq):
            self.bq = bq

        async def run(self):
            await self.bq.put(1)
            await self.bq.put(2)
            # Queue is full (capacity 2). This blocks.
            await self.bq.put(3)

    class Consumer(Process):
        def init(self, bq):
            self.bq = bq
            self.results = []

        async def run(self):
            await self.timeout(5)
            # Getting item 1 should unblock the putter for item 3
            self.results.append(await self.bq.get())
            self.results.append(await self.bq.get())
            self.results.append(await self.bq.get())

    env = Environment()
    bq = BlockingQueue(env, max_capacity=2)
    Producer(env, bq)
    cons = Consumer(env, bq)
    env.run()
    assert cons.results == [1, 2, 3]


def test_blocking_queue_cancel_blocked_put():
    """Test that cancelling a blocked putter's event removes it from putters."""

    class BlockedProducer(Process):
        def init(self, bq):
            self.bq = bq

        async def run(self):
            await self.bq.put(1)  # fills queue
            await self.bq.put(2)  # blocks (queue full)

    class Canceller(Process):
        def init(self, bq):
            self.bq = bq

        async def run(self):
            await self.timeout(5)
            evt, _item = self.bq._putters[0]
            evt.cancel()

    env = Environment()
    bq = BlockingQueue(env, max_capacity=1)
    BlockedProducer(env, bq)
    Canceller(env, bq)
    env.run()
    assert bq._putters == []
