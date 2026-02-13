"""Queue with maximum capacity."""

from asimpy import Environment, Process, Queue


class Filler(Process):
    def init(self, queue: Queue):
        self.queue = queue

    async def run(self):
        for i in range(5):
            added = self.queue.put(f"item-{i}")
            full = self.queue.is_full()
            print(f"put item-{i} added={added} is_full={full}")

        while not self.queue.is_empty():
            item = await self.queue.get()
            print(f"dequeued {item}")


env = Environment()
queue = Queue(env, max_capacity=3)
Filler(env, queue)
env.run()
