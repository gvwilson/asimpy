"""Simulate people waiting on shared resource."""

from asimpy import Environment, Process, Resource


class Customer(Process):
    def init(self, name: str, counter: Resource):
        self.name = name
        self.counter = counter

    async def run(self):
        print(f"{self.env.now:>4}: {self.name} arrives")
        async with self.counter:
            print(f"{self.env.now:>4}: {self.name} starts service")
            await self.env.sleep(5)
            print(f"{self.env.now:>4}: {self.name} leaves")


env = Environment()
counter = Resource(env, capacity=2)

Customer(env, "Alice", counter)
Customer(env, "Bob", counter)
Customer(env, "Charlie", counter)

env.run()
