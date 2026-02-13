"""Simulate producer/consumer with a blocking queue."""

from asimpy import Environment, Process, BlockingQueue


class Producer(Process):
    def init(self, queue: BlockingQueue):
        self.queue = queue

    async def run(self):
        for i in range(5):
            item = f"item-{i}"
            print(f"{self.now:>4}: producer wants to put {item}")
            await self.queue.put(item)
            print(f"{self.now:>4}: producer put {item}")
            await self.timeout(1)


class Consumer(Process):
    def init(self, queue: BlockingQueue):
        self.queue = queue

    async def run(self):
        await self.timeout(3)
        for i in range(5):
            item = await self.queue.get()
            print(f"{self.now:>4}: consumer got {item}")
            await self.timeout(2)


env = Environment()
queue = BlockingQueue(env, max_capacity=2)
Producer(env, queue)
Consumer(env, queue)
env.run()
