"""Simulation environment."""

from dataclasses import dataclass
import heapq
from .actions import BaseAction
from .interrupt import Interrupt
from .process import Process


class Environment:
    """Simulation environment."""

    def __init__(self, log=False):
        self.now = 0
        self._queue = []
        self._log = log

    def start(self, proc):
        """Start a new process immediately."""
        self.schedule(self.now, proc)

    def schedule(self, time, proc):
        heapq.heappush(self._queue, _Pending(time, proc))

    def sleep(self, delay):
        return _Sleep(self, delay)

    def run(self, until=None):
        while self._queue:
            if self._log:
                print(self)

            pending = heapq.heappop(self._queue)

            if until is not None and pending.time > until:
                break

            self.now = pending.time
            proc = pending.proc

            try:
                if proc._interrupt is None:
                    awaited = proc.coro.send(None)
                else:
                    exc, proc._interrupt = proc._interrupt, None
                    awaited = proc.coro.throw(exc)

                awaited.act(proc)

            except StopIteration:
                continue

    def __str__(self):
        return f"Env(t={self.now}, {' | '.join(str(p) for p in self._queue)})"


# ----------------------------------------------------------------------


@dataclass
class _Pending:
    time: float
    proc: Process

    def __lt__(self, other):
        return self.time < other.time

    def __str__(self):
        return f"Pend({self.time}, {self.proc})"


class _Sleep(BaseAction):
    """Wait for a specified simulated time."""

    def __init__(self, env, delay):
        super().__init__(env)
        self.delay = delay

    def act(self, proc):
        self.env.schedule(self.env.now + self.delay, proc)

    def __str__(self):
        return f"_Sleep({self.delay})"
