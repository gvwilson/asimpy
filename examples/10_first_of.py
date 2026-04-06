"""Example: FirstOf races two events and reacts to whichever arrives first."""

from asimpy import Environment, FirstOf, Process, Queue
from _util import example

SERVICE_TIME = 5  # ticks before the server delivers a result
PATIENCE = 3  # ticks a client is willing to wait before leaving


class Server(Process):
    def init(self, queue):
        self._queue = queue

    async def run(self):
        await self.timeout(SERVICE_TIME)
        self._env.log("server", "deliver result")
        await self._queue.put("result")


class Client(Process):
    def init(self, queue):
        self._queue = queue

    async def run(self):
        self._env.log("client", "waiting")
        key, value = await FirstOf(
            self._env,
            served=self._queue.get(),
            timeout=self.timeout(PATIENCE),
        )
        if key == "served":
            self._env.log("client", f"received {value}")
        else:
            self._env.log("client", "timed out, leaving")


def main():
    env = Environment()
    queue = Queue(env)
    Server(env, queue)
    Client(env, queue)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
