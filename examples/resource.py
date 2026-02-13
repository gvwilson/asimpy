"""Simulate people waiting on shared resource."""

from asimpy import Environment, Process, Resource


class WithCustomer(Process):
    def init(self, name: str, counter: Resource):
        self.name = name
        self.counter = counter

    async def run(self):
        print(f"{self.now:>4}: {self.name} arrives")
        async with self.counter:
            print(f"{self.now:>4}: {self.name} starts service")
            await self.timeout(5)
            print(f"{self.now:>4}: {self.name} leaves")


env = Environment()
counter = Resource(env, capacity=2)

WithCustomer(env, "Ahmed", counter)
WithCustomer(env, "Bette", counter)
WithCustomer(env, "Carlos", counter)

env.run()


class DirectCustomer(Process):
    def init(self, name: str, counter: Resource):
        self.name = name
        self.counter = counter

    async def run(self):
        print(f"{self.now:>4}: {self.name} arrives")
        await self.counter.acquire()
        print(f"{self.now:>4}: {self.name} starts service")
        await self.timeout(5)
        print(f"{self.now:>4}: {self.name} leaves")
        await self.counter.release()


print()
env = Environment()
counter = Resource(env, capacity=2)

DirectCustomer(env, "Dave", counter)
DirectCustomer(env, "Eve", counter)
DirectCustomer(env, "Frank", counter)

env.run()
