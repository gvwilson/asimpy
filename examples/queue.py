"""Testing queueing."""

from asimpy import Environment, Process, Queue


class Producer(Process):
    def init(self, queue: Queue):
        self.queue = queue

    async def run(self):
        for i in range(3):
            item = f"item-{i}"
            print(f"producer putting {item} at {self.env.now}")
            await self.queue.put(item)
            print(f"producer sleeping at {self.env.now}")
            await self.env.sleep(2)

    def __str__(self):
        return "producer"


class Consumer(Process):
    def init(self, queue: Queue):
        self.queue = queue

    async def run(self):
        for i in range(3):
            print(f"consumer waiting for {i} at {self.env.now}")
            item = await self.queue.get()
            print(f"consumer got {item} at {self.env.now}")

    def __str__(self):
        return "consumer"


env = Environment()
queue = Queue(env)
Producer(env, queue)
Consumer(env, queue)

env.run()
