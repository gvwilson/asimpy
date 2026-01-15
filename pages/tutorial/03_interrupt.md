# Adding Interrupts

So far, our processes can only suspend themselves
by `await`ing events that eventually complete,
such as timeouts or queue operations.
In real simulations, however, processes often need to be stopped,
preempted, or redirected by other processes.
Our next step is therefore to introduce interrupts.

An interrupt is initiated by one process but delivered to a target process,
where it is raised as an exception.
From the perspective of the target,
an interrupt looks just like a normal Python exception.

## Representing Interrupts

We represent interrupts using a simple exception type with a `cause`,
which can be anything we want:

```python
class Interrupt(Exception):
    def __init__(self, cause):
        self.cause = cause
```

## Changing `Process`

The `Process` class gains a new method:

```
process.interrupt(cause)
```

When called,
it stored a pending `Interrupt` in the target process,
schedules that process to resume immediately,
and causes the exception to be raised at the next `await`.
This last point is important an easy to overlook:
interrupted are only delivered when the process is suspended,
never in the middle of running Python code.

`Process._step` checks whether an interrupt is pending:

```python
if self._interrupt is None:
    evt = self._coro.send(value)
else:
    exc = self._interrupt
    self._interrupt = None
    evt = self._coro.throw(exc)
```

From the process's point of view,
interrupts are handled using normal exception handling:

```python
async def run(self):
    try:
        await self.timeout(10)
    except Interrupt as exc:
        print("interrupted:", exc.cause)
```
