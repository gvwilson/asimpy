from environment import Environment
from process import Process
from simqueue import Queue


class Producer(Process):
    def __init__(self, env, queue):
        self.queue = queue
        super().__init__(env)

    async def run(self):
        for i in range(3):
            print(f"{self.now:>4}: producing {i}")
            await self.queue.put(i)
            await self.timeout(2)


class Consumer(Process):
    def __init__(self, env, queue):
        self.queue = queue
        super().__init__(env)

    async def run(self):
        for i in range(3):
            print(f"{self.now:>4}: waiting for item")
            item = await self.queue.get()
            print(f"{self.now:>4}: got {item}")


env = Environment()
q = Queue(env)

Producer(env, q)
Consumer(env, q)

env.run()
