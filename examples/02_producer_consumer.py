"""Example: producer-consumer."""

from asimpy import Environment, Process, Queue
from _util import example

PRODUCE_INTERVAL = 5  # ticks between successive items being produced
CONSUME_DURATION = 3  # ticks to process each item
NUM_ITEMS = 3  # total items the producer creates before stopping


class Producer(Process):
    def init(self, queue):
        self._queue = queue

    async def run(self):
        for i in range(NUM_ITEMS):
            await self.timeout(PRODUCE_INTERVAL)
            self._env.log("producer", f"create item {i}")
            await self._queue.put(i)


class Consumer(Process):
    def init(self, queue):
        self._queue = queue

    async def run(self):
        while True:
            self._env.log("consumer", "wait for item")
            item = await self._queue.get()
            self._env.log("consumer", f"start item {item}")
            await self.timeout(CONSUME_DURATION)
            self._env.log("consumer", f"finish item {item}")


def main():
    env = Environment()
    queue = Queue(env)
    Producer(env, queue)
    Consumer(env, queue)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
