"""Example: AllOf waits for all named events to complete."""

from asimpy import AllOf, Environment, Process
from _util import example

# Simulated durations for three parallel tasks.
TASK_DURATIONS = {"alpha": 3, "beta": 1, "gamma": 5}


class Coordinator(Process):
    async def run(self):
        self._env.log("coordinator", "launch tasks")
        tasks = {name: self.timeout(dur) for name, dur in TASK_DURATIONS.items()}
        results = await AllOf(self._env, **tasks)
        self._env.log("coordinator", f"all done at keys={sorted(results)}")


def main():
    env = Environment()
    Coordinator(env)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
