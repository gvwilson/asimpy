"""Simulation environment."""

from dataclasses import dataclass
import heapq
from .actions import BaseAction
from .interrupt import Interrupt
from .process import Process


class Environment:
    """Simulation environment."""

    def __init__(self, log=False):
        """
        Construct a new simulation environment.

        Args:
            log: print log messages while executing.
        """

        self.now = 0
        self._queue = []
        self._log = log

    def start(self, proc):
        """
        Start a new process immediately.

        Args:
            proc: `Process`-derived object to schedule and run.
        """

        self.schedule(self.now, proc)

    def schedule(self, time, proc):
        """
        Schedule a process to run at a specified time (*not* after a delay).

        Args:
            time: when the process should be scheduled to run.
            proc: `Process`-derived object to run.
        """

        heapq.heappush(self._queue, _Pending(time, proc))

    def sleep(self, delay):
        """
        Suspend the caller for a specified length of time.

        Args:
            delay: how long to sleep.

        Returns: awaitable representing delay.
        """

        return _Sleep(self, delay)

    def run(self, until=None):
        """
        Run the whole simulation.

        Args:
            until: when to stop (run forever if not provided).
        """

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
        """
        Format environment as printable string.

        Returns: string representation of environment time and queue.
        """

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
