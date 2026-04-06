"""Example: interrupting a process mid-execution."""

from asimpy import Environment, Interrupt, Process
from _util import example

JOB_DURATION = 10  # how long the worker's job takes if uninterrupted
INTERRUPT_AT = 4  # tick at which the manager interrupts the worker


class Worker(Process):
    async def run(self):
        self._env.log("worker", "start job")
        try:
            await self.timeout(JOB_DURATION)
            self._env.log("worker", "finish job")
        except Interrupt as exc:
            elapsed = self.now - 0  # worker started at t=0
            self._env.log(
                "worker", f"interrupted: {exc.cause} (worked {elapsed} ticks)"
            )


class Manager(Process):
    def init(self, worker):
        self._worker = worker

    async def run(self):
        await self.timeout(INTERRUPT_AT)
        self._env.log("manager", "sending interrupt")
        self._worker.interrupt("stop and report")


def main():
    env = Environment()
    # Manager needs a reference to Worker, so Worker must be created first.
    worker = Worker(env)
    Manager(env, worker)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
