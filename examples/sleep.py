"""Repeated sleeping."""

from asimpy import Environment, Process


class Sleeper(Process):
    async def run(self):
        print(f"{self.now:>4}: starts")
        for i in range(3):
            print(f"{self.now:>4}")
            await self.timeout(5)
        print(f"{self.now:>4}: finishes")


env = Environment()
Sleeper(env)
env.run()
