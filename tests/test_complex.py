"""Test complex asimpy scenarios."""

from asimpy import Environment, Queue, Process


def test_producer_consumer_pattern():
    """Test producer-consumer pattern."""

    class Producer(Process):
        def init(self, queue, items):
            self.queue = queue
            self.items = items

        async def run(self):
            for item in self.items:
                await self.timeout(1)
                await self.queue.put(item)

    class Consumer(Process):
        def init(self, queue, count):
            self.queue = queue
            self.count = count
            self.consumed = []

        async def run(self):
            for _ in range(self.count):
                item = await self.queue.get()
                self.consumed.append(item)

    env = Environment()
    q = Queue(env)
    Producer(env, q, [1, 2, 3, 4, 5])
    cons = Consumer(env, q, 5)
    env.run()
    assert cons.consumed == [1, 2, 3, 4, 5]


