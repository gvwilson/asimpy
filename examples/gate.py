"""Simulate people waiting on shared resource."""

from asimpy import Environment, Process, Gate


class Waiter(Process):
    def init(self, name: str, gate: Gate):
        self.name = name
        self.gate = gate

    async def run(self):
        print(f"{self.env.now:>4}: {self.name} arrives")
        await self.gate.wait()
        print(f"{self.env.now:>4}: {self.name} leaves")


class Releaser(Process):
    def init(self, name: str, gate: Gate):
        self.name = name
        self.gate = gate

    async def run(self):
        print(f"{self.env.now:>4}: {self.name} starts")
        await self.env.sleep(2)
        await self.gate.release()
        print(f"{self.env.now:>4}: {self.name} finishes")


env = Environment()
gate = Gate(env)

Waiter(env, "Alice", gate)
Waiter(env, "Bob", gate)
Waiter(env, "Charlie", gate)
Releaser(env, "Zemu", gate)

env.run()
