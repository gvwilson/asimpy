"""Example: container as a shared tank."""

from asimpy import Container, Environment, Process
from _util import example

TANK_CAPACITY = 10  # maximum units the tank can hold
FILL_AMOUNT = 4  # units added by each pump cycle
FILL_INTERVAL = 2  # ticks between pump cycles
DRAIN_AMOUNT = 3  # units consumed by each motor cycle
DRAIN_INTERVAL = 3  # ticks between motor cycles
NUM_CYCLES = 4  # number of drain cycles before the motor stops


class Pump(Process):
    def init(self, tank):
        self._tank = tank

    async def run(self):
        while True:
            await self.timeout(FILL_INTERVAL)
            await self._tank.put(FILL_AMOUNT)
            self._env.log("pump", f"added {FILL_AMOUNT}, level={self._tank.level}")


class Motor(Process):
    def init(self, tank):
        self._tank = tank

    async def run(self):
        for _ in range(NUM_CYCLES):
            await self.timeout(DRAIN_INTERVAL)
            self._env.log("motor", f"request {DRAIN_AMOUNT}, level={self._tank.level}")
            await self._tank.get(DRAIN_AMOUNT)
            self._env.log("motor", f"consumed {DRAIN_AMOUNT}, level={self._tank.level}")


def main():
    env = Environment()
    tank = Container(env, capacity=TANK_CAPACITY, init=5)
    Pump(env, tank)
    Motor(env, tank)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
