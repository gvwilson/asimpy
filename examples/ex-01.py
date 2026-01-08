"""Simulate peopel waiting on shared resource."""

from asimpy import Environment, Resource

async def customer(env, name, counter):
    print(f"{env.now:>4}: {name} arrives")

    async with counter:
        print(f"{env.now:>4}: {name} starts service")
        await env.sleep(5)
        print(f"{env.now:>4}: {name} leaves")


env = Environment()
counter = Resource(env, capacity=2)

env.process(customer(env, "Alice", counter))
env.process(customer(env, "Bob", counter))
env.process(customer(env, "Charlie", counter))

env.run()
