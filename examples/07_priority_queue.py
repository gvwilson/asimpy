"""Example: priority queue serving jobs in priority order."""

from asimpy import Environment, PriorityQueue, Process
from _util import example

SERVICE_DURATION = 2  # ticks to process each job
# Each entry is (priority, label): lower priority number is served first.
JOBS = [
    (3, "low-A"),
    (1, "high-B"),
    (2, "mid-C"),
    (1, "high-D"),
]


class Submitter(Process):
    """Submits all jobs at t=0 then stops."""

    def init(self, queue):
        self._queue = queue

    async def run(self):
        for priority, label in JOBS:
            self._env.log("submitter", f"submit ({priority}, {label})")
            await self._queue.put((priority, label))


class Server(Process):
    """Processes jobs one at a time in priority order."""

    def init(self, queue):
        self._queue = queue

    async def run(self):
        while True:
            priority, label = await self._queue.get()
            self._env.log("server", f"start ({priority}, {label})")
            await self.timeout(SERVICE_DURATION)
            self._env.log("server", f"finish ({priority}, {label})")


def main():
    env = Environment()
    queue = PriorityQueue(env)
    Submitter(env, queue)
    Server(env, queue)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
