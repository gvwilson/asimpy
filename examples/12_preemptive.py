"""Example: preemptive resource where a high-priority process evicts a low-priority one."""

from asimpy import Environment, Interrupt, Preempted, PreemptiveResource, Process
from _util import example

RESOURCE_CAPACITY = 1  # single-slot resource
LOW_PRIORITY = 2  # lower priority (higher number)
HIGH_PRIORITY = 0  # higher priority (lower number)
LOW_WORK = 8  # ticks the low-priority worker needs
HIGH_ARRIVE = 3  # tick at which the high-priority worker arrives
HIGH_WORK = 2  # ticks the high-priority worker needs


class LowPriorityWorker(Process):
    def init(self, resource):
        self._resource = resource
        self._remaining = LOW_WORK

    async def run(self):
        while self._remaining > 0:
            self._env.log("low", f"acquire (remaining={self._remaining})")
            try:
                await self._resource.acquire(priority=LOW_PRIORITY)
                self._env.log("low", "working")
                await self.timeout(self._remaining)
                self._remaining = 0
                self._resource.release()
                self._env.log("low", "done")
            except Interrupt as exc:
                if isinstance(exc.cause, Preempted):
                    used = self.now - exc.cause.usage_since
                    self._remaining -= used
                    self._env.log(
                        "low",
                        f"preempted after {used} ticks, {self._remaining} remaining",
                    )
                else:
                    raise


class HighPriorityWorker(Process):
    def init(self, resource):
        self._resource = resource

    async def run(self):
        await self.timeout(HIGH_ARRIVE)
        self._env.log("high", "acquire (preempt=True)")
        await self._resource.acquire(priority=HIGH_PRIORITY, preempt=True)
        self._env.log("high", "working")
        await self.timeout(HIGH_WORK)
        self._resource.release()
        self._env.log("high", "done")


def main():
    env = Environment()
    resource = PreemptiveResource(env, capacity=RESOURCE_CAPACITY)
    LowPriorityWorker(env, resource)
    HighPriorityWorker(env, resource)
    env.run()
    return env


if __name__ == "__main__":
    example(main)
