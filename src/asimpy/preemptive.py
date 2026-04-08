"""Preemptive shared resource."""

import bisect
import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .event import _CANCELLED, Event

if TYPE_CHECKING:
    from .environment import Environment
    from .process import Process


@dataclass
class Preempted:
    """Interrupt cause delivered when a process is evicted from a PreemptiveResource.

    Attributes:
        by: the process that caused the preemption.
        usage_since: simulation time when the preempted process acquired the resource.
    """

    by: "Process"
    usage_since: float


class PreemptiveResource:
    """Shared resource where higher-priority processes can preempt lower-priority users.

    Priority is an integer; lower values are served first (0 is highest priority).
    When a new acquire request has better priority than the worst current user
    and `preempt=True`, that user is interrupted with a `Preempted` cause and
    removed from the resource.  The preempted process is responsible for catching
    the `Interrupt`, tracking remaining work, and re-acquiring.

    Do *not* call `release()` when handling a `Preempted` interrupt:
    the preempted process has already been removed from the user list by the preemptor.
    """

    # Class-level counter ensures stable FIFO ordering among equal-priority requests.
    _seq = itertools.count()

    def __init__(self, env: "Environment", capacity: int = 1):
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._env = env
        self.capacity = capacity
        self._users: list = []  # sorted list of [priority, seq, usage_since, process]
        self._waiters: list = []  # sorted list of [priority, seq, process, event]

    @property
    def count(self) -> int:
        """Current number of active users."""
        return len(self._users)

    async def acquire(self, priority: int = 0, preempt: bool = True) -> None:
        """Acquire one unit of the resource.

        Must be called from within a Process.run() coroutine; the calling
        process is identified via env._active_process.

        Args:
            priority: lower value = higher priority (0 is best).
            preempt: if True, may interrupt the lowest-priority current user
                when the resource is full and that user has lower priority
                than this request.
        """
        process = self._env._active_process
        assert process is not None
        seq = next(PreemptiveResource._seq)

        if len(self._users) < self.capacity:
            user_rec = [priority, seq, self._env.now, process]
            bisect.insort(self._users, user_rec)
            evt = Event(self._env)
            # _on_cancel removes the user record if FirstOf later discards this event.
            evt._on_cancel = lambda v, rec=user_rec: self._users.remove(rec)
            evt.succeed()
            await evt
            return

        if preempt and self._users:
            worst = self._users[-1]  # highest priority number = worst priority
            if worst[0] > priority:
                self._users.remove(worst)
                preempted_proc = worst[3]
                preempted_since = worst[2]
                user_rec = [priority, seq, self._env.now, process]
                bisect.insort(self._users, user_rec)
                evt = Event(self._env)
                evt._on_cancel = lambda v, rec=user_rec: self._users.remove(rec)
                evt.succeed()
                if preempted_proc is not None:
                    preempted_proc.interrupt(
                        Preempted(by=process, usage_since=preempted_since)
                    )
                await evt
                return

        evt = Event(self._env)
        waiter_rec = [priority, seq, process, evt]
        bisect.insort(self._waiters, waiter_rec)
        # Lazy deletion in release() skips cancelled entries; no _on_cancel needed.
        await evt

    def release(self) -> None:
        """Release one unit of the resource.

        The calling process is identified via env._active_process.
        Do not call this when handling a Preempted interrupt: the preempted
        process has already been removed from the user list by the preemptor.

        Raises:
            RuntimeError: if the calling process is not a current user.
        """
        process = self._env._active_process
        for i, user in enumerate(self._users):
            if user[3] is process:
                del self._users[i]
                break
        else:
            raise RuntimeError(f"{process} is not a current user of this resource")

        # Lazy deletion: skip waiters whose events were cancelled.
        while self._waiters:
            waiter = self._waiters[0]
            if waiter[3]._value is _CANCELLED:
                self._waiters.pop(0)
                continue
            self._waiters.pop(0)
            w_priority, w_seq, w_process, w_evt = waiter
            user_rec = [w_priority, w_seq, self._env.now, w_process]
            bisect.insort(self._users, user_rec)
            w_evt.succeed()
            break
