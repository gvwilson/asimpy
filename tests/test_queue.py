"""Test asimpy queue."""

import pytest
from asimpy import Environment, Queue, Process


def test_queue_initialization():
    """Test queue initialization."""
    env = Environment()
    q = Queue(env)
    assert len(q._items) == 0
    assert len(q._getters) == 0


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
    q = Queue(env)  # Default: max_capacity=None
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert len(cons.results) == 100
    assert cons.results == list(range(100))


def test_queue_explicit_none_capacity():
    """Test queue with explicitly set None capacity."""

    class QueueUser(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            for i in range(10):
                await self.q.put(i)
            for _ in range(10):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=None)
    proc = QueueUser(env, q)
    env.run()
    assert len(proc.results) == 10


def test_queue_max_capacity_basic():
    """Test queue with max_capacity set to positive integer."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(5):
                await self.q.put(i)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(1)
            # Try to get all 5 items, but only 3 should be available
            for _ in range(3):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=3)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    # Only first 3 items should be in queue (items 3 and 4 were discarded)
    assert len(cons.results) == 3
    assert cons.results == [0, 1, 2]
    assert len(q._items) == 0  # All items consumed


def test_queue_max_capacity_discard_excess():
    """Test that items beyond max_capacity are discarded."""

    class Producer(Process):
        def init(self, q):
            self.q = q
            self.put_count = 0

        async def run(self):
            for i in range(10):
                await self.q.put(i)
                self.put_count += 1

    env = Environment()
    q = Queue(env, max_capacity=4)
    prod = Producer(env, q)
    env.run()
    assert prod.put_count == 10  # All puts executed
    assert len(q._items) == 4  # Only 4 items stored
    assert q._items == [0, 1, 2, 3]  # First 4 items


def test_queue_max_capacity_one():
    """Test queue with max_capacity of 1."""

    class QueueUser(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.q.put("first")
            await self.q.put("second")
            await self.q.put("third")

    env = Environment()
    q = Queue(env, max_capacity=1)
    QueueUser(env, q)
    env.run()
    assert len(q._items) == 1
    assert q._items[0] == "first"


def test_queue_max_capacity_with_waiting_getters():
    """Test that max_capacity doesn't affect direct delivery to waiting getters."""

    class Consumer(Process):
        def init(self, q, consumer_id, results_dict):
            self.q = q
            self.consumer_id = consumer_id
            self.results_dict = results_dict

        async def run(self):
            # Each consumer waits for one item
            item = await self.q.get()
            self.results_dict[self.consumer_id] = item

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(1)
            # Put 5 items while 5 consumers are waiting
            for i in range(5):
                await self.q.put(i)

    env = Environment()
    q = Queue(env, max_capacity=2)  # Small capacity
    results = {}
    
    # Create 5 consumers that each wait for one item
    for i in range(5):
        Consumer(env, q, i, results)
    
    Producer(env, q)
    env.run()
    
    # All items should be delivered directly to waiting getters
    # Capacity limit doesn't apply to direct delivery
    assert len(results) == 5
    assert sorted(results.values()) == [0, 1, 2, 3, 4]


def test_queue_max_capacity_mixed_scenario():
    """Test queue with mix of waiting getters and stored items."""

    class Consumer(Process):
        def init(self, q, delay):
            self.q = q
            self.delay = delay
            self.results = []

        async def run(self):
            await self.timeout(self.delay)
            for _ in range(5):
                self.results.append(await self.q.get())

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            # Put items immediately (will be stored)
            for i in range(7):
                await self.q.put(i)

    env = Environment()
    q = Queue(env, max_capacity=3)
    Producer(env, q)  # Puts 7 items, only 3 stored
    cons = Consumer(env, q, delay=5)  # Consumes after delay
    env.run()
    # Should only get first 3 items
    assert len(cons.results) == 3
    assert cons.results == [0, 1, 2]


def test_queue_max_capacity_zero_invalid():
    """Test that max_capacity of 0 raises assertion error."""
    env = Environment()
    with pytest.raises(AssertionError):
        Queue(env, max_capacity=0)


def test_queue_max_capacity_negative_invalid():
    """Test that negative max_capacity raises assertion error."""
    env = Environment()
    with pytest.raises(AssertionError):
        Queue(env, max_capacity=-1)


def test_queue_max_capacity_refill_after_consumption():
    """Test that queue can be refilled after items are consumed."""

    class ProducerConsumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            # Fill queue to capacity
            for i in range(3):
                await self.q.put(i)
            
            # Consume one item
            self.results.append(await self.q.get())
            
            # Add two more items
            await self.q.put(10)
            await self.q.put(11)
            
            # Consume remaining
            for _ in range(3):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=3)
    proc = ProducerConsumer(env, q)
    env.run()
    assert proc.results == [0, 1, 2, 10]


def test_queue_max_capacity_concurrent_producers():
    """Test max_capacity with multiple producers."""

    class Producer(Process):
        def init(self, q, value):
            self.q = q
            self.value = value

        async def run(self):
            await self.q.put(self.value)

    env = Environment()
    q = Queue(env, max_capacity=2)
    
    Producer(env, q, "A")
    Producer(env, q, "B")
    Producer(env, q, "C")
    Producer(env, q, "D")
    
    env.run()
    assert len(q._items) == 2


def test_queue_max_capacity_large_value():
    """Test queue with large max_capacity value."""

    class QueueUser(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(150):
                await self.q.put(i)

    env = Environment()
    q = Queue(env, max_capacity=100)
    QueueUser(env, q)
    env.run()
    assert len(q._items) == 100
    assert q._items[0] == 0
    assert q._items[99] == 99


def test_queue_max_capacity_with_fifo_order():
    """Test that FIFO order is maintained with max_capacity."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(10):
                await self.q.put(i)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(1)
            for _ in range(5):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=5)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    # Should get first 5 items in FIFO order
    assert cons.results == [0, 1, 2, 3, 4]


def test_queue_max_capacity_empty_queue_behavior():
    """Test that empty queue behavior is unchanged with max_capacity."""

    class DelayedProducer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(10)
            await self.q.put(42)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.result = None
            self.get_time = None

        async def run(self):
            self.result = await self.q.get()
            self.get_time = self.now

    env = Environment()
    q = Queue(env, max_capacity=3)
    cons = Consumer(env, q)
    DelayedProducer(env, q)
    env.run()
    assert cons.result == 42
    assert cons.get_time == 10


def test_priority_queue_max_capacity():
    """Test priority queue with max_capacity."""

    class PQUser(Process):
        def init(self, pq):
            self.pq = pq
            self.results = []

        async def run(self):
            # Put items in non-sorted order
            await self.pq.put(5)
            await self.pq.put(2)
            await self.pq.put(8)
            await self.pq.put(1)
            await self.pq.put(9)

            # Get items - should be sorted and limited to capacity
            for _ in range(3):
                self.results.append(await self.pq.get())

    env = Environment()
    pq = Queue(env, max_capacity=3, priority=True)
    proc = PQUser(env, pq)
    env.run()
    assert pq._dropped == 2
    assert proc.results == [1, 2, 5]


def test_queue_max_capacity_stress_test():
    """Stress test with many operations at capacity limit."""

    class StressProducer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(1000):
                await self.q.put(i)

    class StressConsumer(Process):
        def init(self, q, count):
            self.q = q
            self.count = count
            self.results = []

        async def run(self):
            await self.timeout(1)
            for _ in range(self.count):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=10)
    StressProducer(env, q)
    cons = StressConsumer(env, q, 10)
    env.run()
    assert len(cons.results) == 10
    assert cons.results == list(range(10))


def test_queue_discard_false_blocks_when_full():
    """Test that put blocks when queue is full and discard is False."""

    class Producer(Process):
        def init(self, q):
            self.q = q
            self.put_times = []

        async def run(self):
            for i in range(5):
                await self.q.put(i)
                self.put_times.append(self.now)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(10)
            for _ in range(5):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=2, discard=False)
    prod = Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    # First 2 puts succeed immediately at time 0
    # Puts 3-5 block until consumer starts getting at time 10
    assert prod.put_times[0] == 0
    assert prod.put_times[1] == 0
    assert prod.put_times[2] == 10
    assert prod.put_times[3] == 10
    assert prod.put_times[4] == 10
    assert cons.results == [0, 1, 2, 3, 4]


def test_queue_discard_false_put_returns_true():
    """Test that blocked put returns True when it eventually succeeds."""

    class Producer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            for i in range(3):
                result = await self.q.put(i)
                self.results.append(result)

    class Consumer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.timeout(1)
            for _ in range(3):
                await self.q.get()

    env = Environment()
    q = Queue(env, max_capacity=1, discard=False)
    prod = Producer(env, q)
    Consumer(env, q)
    env.run()
    assert prod.results == [True, True, True]


def test_queue_discard_false_multiple_blocked_putters():
    """Test multiple producers blocking on a full queue."""

    class Producer(Process):
        def init(self, q, value, log):
            self.q = q
            self.value = value
            self.log = log

        async def run(self):
            await self.q.put(self.value)
            self.log.append((self.value, self.now))

    class Consumer(Process):
        def init(self, q, results):
            self.q = q
            self.results = results

        async def run(self):
            await self.timeout(5)
            for _ in range(4):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=1, discard=False)
    log = []
    results = []
    # First producer fills the queue, others block
    Producer(env, q, "A", log)
    Producer(env, q, "B", log)
    Producer(env, q, "C", log)
    Producer(env, q, "D", log)
    Consumer(env, q, results)
    env.run()
    assert results == ["A", "B", "C", "D"]
    # A completes immediately, B-D unblock when consumer gets
    assert log[0] == ("A", 0)
    assert log[1][1] == 5
    assert log[2][1] == 5
    assert log[3][1] == 5


def test_queue_discard_false_fifo_order_preserved():
    """Test that FIFO order is preserved when putters block."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(6):
                await self.q.put(i)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(1)
            for _ in range(6):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=3, discard=False)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert cons.results == [0, 1, 2, 3, 4, 5]


def test_queue_discard_false_priority():
    """Test blocking put with priority queue."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.q.put(30)
            await self.q.put(10)
            await self.q.put(20)
            # Queue is now full [10, 20, 30]; next put blocks
            await self.q.put(5)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            await self.timeout(1)
            for _ in range(4):
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=3, priority=True, discard=False)
    Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    # First get pops 10 (smallest in queue), which wakes putter with 5.
    # 5 is insorted into [20, 30] -> [5, 20, 30].
    # Subsequent gets pop 5, 20, 30.
    assert cons.results == [10, 5, 20, 30]


def test_queue_discard_false_no_effect_without_capacity():
    """Test that discard=False has no effect when max_capacity is None."""

    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(100):
                await self.q.put(i)

    env = Environment()
    q = Queue(env, discard=False)
    Producer(env, q)
    env.run()
    assert len(q._items) == 100


def test_queue_discard_false_interleaved_put_get():
    """Test interleaved blocking puts and gets."""

    class Producer(Process):
        def init(self, q):
            self.q = q
            self.put_times = []

        async def run(self):
            for i in range(4):
                await self.q.put(i)
                self.put_times.append(self.now)

    class Consumer(Process):
        def init(self, q):
            self.q = q
            self.results = []

        async def run(self):
            # Get one item every 5 ticks
            for _ in range(4):
                await self.timeout(5)
                self.results.append(await self.q.get())

    env = Environment()
    q = Queue(env, max_capacity=1, discard=False)
    prod = Producer(env, q)
    cons = Consumer(env, q)
    env.run()
    assert cons.results == [0, 1, 2, 3]
    # First put at 0, then each subsequent put unblocks when consumer gets
    assert prod.put_times[0] == 0
    assert prod.put_times[1] == 5
    assert prod.put_times[2] == 10
    assert prod.put_times[3] == 15


def test_queue_cancel_blocked_put():
    """Test that cancelling a blocked put removes it from putters."""

    class Filler(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            await self.q.put(1)
            await self.q.put(2)

    env = Environment()
    q = Queue(env, max_capacity=1, discard=False)
    Filler(env, q)
    env.run()
    assert len(q._putters) == 1
    evt, item = q._putters[0]
    evt.cancel()
    assert len(q._putters) == 0
