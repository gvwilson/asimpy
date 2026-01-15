from environment import Environment
from process import Process


class Sleeper(Process):
    async def run(self):
        print(f"{self.now:>4}: start")
        for i in range(3):
            await self.timeout(5)
            print(f"{self.now:>4}: woke up {i}")
        print(f"{self.now:>4}: end")


env = Environment()
Sleeper(env)
env.run()
