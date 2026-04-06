"""Example: sleeps once for five ticks."""

from asimpy import Environment, Process
from _util import example

SLEEP_DURATION = 5  # simulated time units per sleep


class Sleeper(Process):
    async def run(self):
        print(f"t={self.now:02d}: start")
        await self.timeout(SLEEP_DURATION)
        print(f"t={self.now:02d}: end")


def main():
    env = Environment()
    Sleeper(env)
    env.run()


if __name__ == "__main__":
    example(main)
