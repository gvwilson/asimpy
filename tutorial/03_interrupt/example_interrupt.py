from environment import Environment
from interrupt import Interrupt
from process import Process


class Actor(Process):
    async def run(self):
        print(f"{self.now:>4}: actor start")
        try:
            print(f"{self.now:>4}: actor sleeping")
            await self.timeout(10)
            print(f"{self.now:>4}: actor woke normally")
        except Interrupt as exc:
            print(f"{self.now:>4}: actor interrupted with {exc.cause}")
        print(f"{self.now:>4}: actor end")


class Interrupter(Process):
    def __init__(self, env, other):
        self.other = other
        super().__init__(env)

    async def run(self):
        await self.timeout(3)
        print(f"{self.now:>4}: sending interrupt")
        self.other.interrupt("wake up!")


env = Environment()
actor = Actor(env)
Interrupter(env, actor)
env.run()
