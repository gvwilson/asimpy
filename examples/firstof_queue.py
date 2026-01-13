from asimpy import Environment, Process, Queue, FirstOf


class Tester(Process):
    def init(self, q1: Queue, q2: Queue):
        self.q1 = q1
        self.q2 = q2

    async def run(self):
        item = await FirstOf(
            self._env,
            a=self.q1.get(),
            b=self.q2.get(),
        )
        print(f"winner got {item}")

        # Drain remaining items
        if self.q1._items:
            print("q1 still has:", self.q1._items)
        if self.q2._items:
            print("q2 still has:", self.q2._items)


env = Environment()
q1 = Queue(env)
q2 = Queue(env)

env._immediate(lambda: q1._items.append("A"))
env._immediate(lambda: q2._items.append("B"))

Tester(env, q1, q2)
env.run()
