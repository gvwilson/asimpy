"""Example: barrier."""

from asimpy import Barrier, Environment, Process
from _util import example

NUM_WAITERS = 3  # number of waiting processes


class Waiter(Process):
    def init(self, barrier, delay):
        self._barrier = barrier
        self._delay = delay

    async def run(self):
        await self.timeout(self._delay)
        self._env.log(f"waiter {self._delay}", "waiting")
        await self._barrier.wait()
        self._env.log(f"waiter {self._delay}", "released")


class Releaser(Process):
    def init(self, barrier, delay):
        self._barrier = barrier
        self._delay = delay

    async def run(self):
        await self.timeout(self._delay)
        self._env.log("releaser", "releasing")
        self._barrier.release()


def main():
    env = Environment()
    barrier = Barrier(env)
    for i in range(NUM_WAITERS):
        Waiter(env, barrier, i)
    Releaser(env, barrier, NUM_WAITERS)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
