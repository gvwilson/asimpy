"""Test asimpy priority queue."""

from asimpy import Environment, PriorityQueue, Process


def test_priority_queue_ordering():
    """Test that items come out in priority order."""

    class PQUser(Process):
        def init(self, pq):
            self.pq = pq
            self.results = []

        async def run(self):
            await self.pq.put(3)
            await self.pq.put(1)
            await self.pq.put(2)
            self.results.append(await self.pq.get())
            self.results.append(await self.pq.get())
            self.results.append(await self.pq.get())

    env = Environment()
    pq = PriorityQueue(env)
    proc = PQUser(env, pq)
    env.run()
    assert proc.results == [1, 2, 3]


def test_priority_queue_with_tuples():
    """Test priority queue with tuple items."""

    class TupleUser(Process):
        def init(self, pq):
            self.pq = pq
            self.results = []

        async def run(self):
            await self.pq.put((2, "second"))
            await self.pq.put((1, "first"))
            await self.pq.put((3, "third"))
            self.results.append(await self.pq.get())
            self.results.append(await self.pq.get())

    env = Environment()
    pq = PriorityQueue(env)
    proc = TupleUser(env, pq)
    env.run()
    assert proc.results[0] == (1, "first")
    assert proc.results[1] == (2, "second")


def test_priority_queue_capacity():
    """Test priority queue with capacity blocks when full."""

    class PQUser(Process):
        def init(self, pq):
            self.pq = pq
            self.results = []

        async def run(self):
            await self.pq.put(5)
            await self.pq.put(2)
            await self.pq.put(8)

            for _ in range(3):
                self.results.append(await self.pq.get())

    env = Environment()
    pq = PriorityQueue(env, capacity=3)
    proc = PQUser(env, pq)
    env.run()
    assert proc.results == [2, 5, 8]


def test_priority_queue_is_empty():
    """PriorityQueue.is_empty() returns True when empty, False otherwise."""
    env = Environment()
    pq = PriorityQueue(env)
    assert pq.is_empty()
    pq._items.append(42)
    assert not pq.is_empty()


def test_priority_queue_put_back():
    """PriorityQueue._put_back() re-inserts an item in sorted order."""
    env = Environment()
    pq = PriorityQueue(env)
    pq._items = [1, 3, 5]
    pq._put_back(2)
    assert pq._items == [1, 2, 3, 5]
