from asimpy import AllOf, Environment, Process


class Waiter(Process):
    async def run(self):
        print(f"{self.env.now:>4}: starts")
        await AllOf(
            self.env,
            a=self.env.timeout(5),
            b=self.env.timeout(10),
        )
        print(f"{self.env.now:>4}: finishes")


env = Environment()
Waiter(env)
env.run()
