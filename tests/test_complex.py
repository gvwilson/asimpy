"""Test complex asimpy scenarios."""

from asimpy import Environment, Queue, Resource, Process


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


def test_resource_sharing():
    """Test multiple processes sharing resource."""
    from asimpy import Environment, Process

    class Worker(Process):
        def init(self, resource, work_id, log):
            self.resource = resource
            self.work_id = work_id
            self.log = log

        async def run(self):
            await self.resource.acquire()
            self.log.append(("start", self.work_id, self.now))
            await self.timeout(5)
            self.log.append(("end", self.work_id, self.now))
            await self.resource.release()

    env = Environment()
    res = Resource(env, capacity=2)
    log = []

    Worker(env, res, 1, log)
    Worker(env, res, 2, log)
    Worker(env, res, 3, log)

    env.run()
    assert len(log) == 6
