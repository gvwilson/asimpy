"""Example: sleeps for 5 ticks, three times."""

from asimpy import Environment, Process
from _util import example

SLEEP_DURATION = 5  # simulated time units per sleep
SLEEP_COUNT = 3     # number of times to sleep


class Sleeper(Process):
    async def run(self):
        for i in range(SLEEP_COUNT):
            await self.timeout(SLEEP_DURATION)
            print(f"t={self.now:02d}: loop {i}")


def main():
    env = Environment()
    Sleeper(env)
    env.run()


if __name__ == "__main__":
    example(main)
