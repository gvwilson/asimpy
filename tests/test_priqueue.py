"""Test asimpy priority queue."""

from asimpy import Environment, Queue, Process


def test_priority_queue_initialization():
    """Test priority queue initialization."""
    env = Environment()
    pq = Queue(env, priority=True)
    assert len(pq._items) == 0


def test_priority_queue_ordering():
    """Test that items come out in priority order."""

    class PQUser(Process):
        def init(self, pq):
            self.pq = pq
            self.results = []

        async def run(self):
            self.pq.put(3)
            self.pq.put(1)
            self.pq.put(2)
            self.results.append(await self.pq.get())
            self.results.append(await self.pq.get())
            self.results.append(await self.pq.get())

    env = Environment()
    pq = Queue(env, priority=True)
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
            self.pq.put((2, "second"))
            self.pq.put((1, "first"))
            self.pq.put((3, "third"))
            self.results.append(await self.pq.get())
            self.results.append(await self.pq.get())

    env = Environment()
    pq = Queue(env, priority=True)
    proc = TupleUser(env, pq)
    env.run()
    assert proc.results[0] == (1, "first")
    assert proc.results[1] == (2, "second")
