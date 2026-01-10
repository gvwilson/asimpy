"""Simulate interrupts."""

from asimpy import Environment, Interrupt, Process


class Actor(Process):
    async def run(self):
        print(f"{self.env.now:>4}: actor start")
        for i in range(4):
            try:
                print(f"{self.env.now:>4}/{i}: actor about to sleep")
                await self.env.sleep(2)
                print(f"{self.env.now:>4}/{i}: actor wakes with {self._interrupt}")
            except Interrupt as exc:
                print(f"{self.env.now:>4}/{i}: actor interrupted with {exc.cause}")
        print(f"{self.env.now:>4}: actor end")

    def __str__(self):
        return f"actor+{self._interrupt}"


class Interrupter(Process):
    def init(self, other: Process):
        self.other = other

    async def run(self):
        print(f"{self.env.now:>4}: interrupter start")
        for i in range(2):
            await self.env.sleep(3)
            print(f"{self.env.now:>4}/{i}: scheduling interrupt")
            self.other.interrupt("message")
        print(f"{self.env.now:>4}: interrupter end")

    def __str__(self):
        return f"interrupter+{self._interrupt}"


env = Environment(logging=True)
actor = Actor(env)
Interrupter(env, actor)
env.run()
