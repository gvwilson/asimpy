"""Simulate people waiting on shared resource."""

from asimpy import Environment, Process, Barrier


class Waiter(Process):
    def init(self, name: str, barrier: Barrier):
        self.name = name
        self.barrier = barrier

    async def run(self):
        print(f"{self.now:>4}: {self.name} arrives")
        await self.barrier.wait()
        print(f"{self.now:>4}: {self.name} leaves")


class Releaser(Process):
    def init(self, name: str, barrier: Barrier):
        self.name = name
        self.barrier = barrier

    async def run(self):
        print(f"{self.now:>4}: {self.name} starts")
        await self.timeout(2)
        await self.barrier.release()
        print(f"{self.now:>4}: {self.name} finishes")


env = Environment()
barrier = Barrier(env)

Waiter(env, "Alice", barrier)
Waiter(env, "Bob", barrier)
Waiter(env, "Charlie", barrier)
Releaser(env, "Zemu", barrier)

env.run()
