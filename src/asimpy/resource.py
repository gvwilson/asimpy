"""Shared resource."""

from .event import Event


class Resource:
    def __init__(self, env, capacity=1):
        self._env = env
        self.capacity = capacity
        self._count = 0
        self._waiters = []

    async def acquire(self):
        # Case 1: capacity available → reserve immediately
        if self._count < self.capacity:
            self._count += 1
            evt = Event(self._env)

            def cancel():
                # Roll back reservation
                self._count -= 1

            evt._on_cancel = cancel
            self._env._immediate(evt.succeed)
            await evt
            return

        # Case 2: must wait
        evt = Event(self._env)
        self._waiters.append(evt)

        def cancel():
            # Remove from waiter list if canceled
            if evt in self._waiters:
                self._waiters.remove(evt)

        evt._on_cancel = cancel

        await evt

        # Commit acquisition *after* winning
        self._count += 1

    async def release(self):
        self._count -= 1
        if self._waiters:
            evt = self._waiters.pop(0)
            evt.succeed()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()
