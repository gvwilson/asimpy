"""Example: store with heterogeneous items and filter-based retrieval."""

from asimpy import Environment, Process, Store
from _util import example

ITEMS = ["red", "blue", "red", "blue", "red"]  # items added at t=1, 2, 3, 4, 5


class Stacker(Process):
    """Adds items to the store one per tick."""

    def init(self, store):
        self._store = store

    async def run(self):
        for item in ITEMS:
            await self.timeout(1)
            await self._store.put(item)
            self._env.log("stacker", f"put {item}")


class RedPicker(Process):
    """Retrieves only red items from the store."""

    def init(self, store):
        self._store = store

    async def run(self):
        for _ in range(3):
            item = await self._store.get(filter=lambda x: x == "red")
            self._env.log("red-picker", f"got {item}")


class BluePicker(Process):
    """Retrieves only blue items from the store."""

    def init(self, store):
        self._store = store

    async def run(self):
        for _ in range(2):
            item = await self._store.get(filter=lambda x: x == "blue")
            self._env.log("blue-picker", f"got {item}")


def main():
    env = Environment()
    store = Store(env)
    Stacker(env, store)
    RedPicker(env, store)
    BluePicker(env, store)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
