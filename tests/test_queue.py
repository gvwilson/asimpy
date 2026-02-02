"""Test asimpy queue."""

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
