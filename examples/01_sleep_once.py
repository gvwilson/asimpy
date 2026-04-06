"""Example: sleep once for five ticks."""

from asimpy import Environment, Process
from _util import example

SLEEP_DURATION = 5  # simulated time units per sleep


class Sleeper(Process):
    async def run(self):
        self._env.log("sleeper", "start")
        await self.timeout(SLEEP_DURATION)
        self._env.log("sleeper", "end")


def main():
    env = Environment()
    Sleeper(env)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
