"""Example: shared resource with limited capacity."""

from asimpy import Environment, Process, Resource
from _util import example

NUM_WORKERS = 4  # total number of workers competing for the resource
CAPACITY = 2  # number of concurrent slots on the shared resource
WORK_DURATION = 3  # ticks each worker spends holding the resource


class Worker(Process):
    def init(self, name, resource, delay):
        self._name = name
        self._resource = resource
        self._delay = delay

    async def run(self):
        await self.timeout(self._delay)
        self._env.log(self._name, "request")
        await self._resource.acquire()
        self._env.log(self._name, "start")
        await self.timeout(WORK_DURATION)
        self._resource.release()
        self._env.log(self._name, "done")


def main():
    env = Environment()
    resource = Resource(env, capacity=CAPACITY)
    for i in range(NUM_WORKERS):
        Worker(env, f"worker {i}", resource, delay=i)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
