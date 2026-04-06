"""Example: producer-consumer."""

from asimpy import Environment, Process, Queue
from _util import example

PRODUCE_INTERVAL = 5  # ticks between successive items being produced
CONSUME_DURATION = 3  # ticks to process each item
NUM_ITEMS = 3         # total items the producer creates before stopping


class Producer(Process):
    def init(self, queue):
        self._queue = queue

    async def run(self):
        for i in range(NUM_ITEMS):
            await self.timeout(PRODUCE_INTERVAL)
            print(f"t={self.now:02d}: producer: create item {i}")
            await self._queue.put(i)


class Consumer(Process):
    def init(self, queue):
        self._queue = queue

    async def run(self):
        while True:
            print(f"t={self.now:02d}: consumer: wait for item")
            item = await self._queue.get()
            print(f"t={self.now:02d}: consumer: start processing item {item}")
            await self.timeout(CONSUME_DURATION)
            print(f"t={self.now:02d}: consumer: finish processing item {item}")


def main():
    env = Environment()
    queue = Queue(env)
    Producer(env, queue)
    Consumer(env, queue)
    env.run()


if __name__ == "__main__":
    example(main)
