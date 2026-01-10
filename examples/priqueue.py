"""Testing queueing."""

from asimpy import Environment, Process, PriorityQueue


class Producer(Process):
    def init(self, queue: PriorityQueue):
        self.queue = queue

    async def run(self):
        for i in range(3, 0, -1):
            print(f"producer putting {i} at {self.env.now}")
            await self.queue.put(i)


class Consumer(Process):
    def init(self, queue: PriorityQueue):
        self.queue = queue

    async def run(self):
        await self.env.sleep(1)
        for i in range(3):
            item = await self.queue.get()
            print(f"consumer got {item}")


env = Environment()
queue = PriorityQueue(env)
Producer(env, queue)
Consumer(env, queue)

env.run()
