from asimpy import AllOf, Environment, Process


class Waiter(Process):
    async def run(self):
        print(f"{self.now:>4}: starts")
        await AllOf(self._env, a=self.timeout(5), b=self.timeout(10))
        print(f"{self.now:>4}: finishes")


env = Environment()
Waiter(env)
env.run()
