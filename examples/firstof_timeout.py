from asimpy import Environment, Process, FirstOf


class Waiter(Process):
    async def run(self):
        print(f"{self.now:>4}: starts")
        name, value = await FirstOf(
            self._env,
            a=self.timeout(5),
            b=self.timeout(10),
        )
        print(f"{self.now:>4}: first finished -> {name}")
        print(f"{self.now:>4}: finishes")


env = Environment()
Waiter(env)
env.run()
