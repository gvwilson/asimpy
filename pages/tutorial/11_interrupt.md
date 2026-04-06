# Interrupt

## Source and Output

```python
--8<-- "examples/11_interrupt.py"
```

--8<-- "output/11_interrupt.txt"

## Key Points

1.  `process.interrupt(cause)` throws an `Interrupt` exception into
    the target process at its current `await` point.  `cause` can be
    any Python object.

2.  The process must catch `Interrupt`.  An uncaught interrupt
    terminates the process and re-raises the exception.

3.  The worker's `await self.timeout(JOB_DURATION)` is cancelled when the
    interrupt arrives at t=4.  Execution resumes at the `except Interrupt`
    block, not after the `await`.

4.  `interrupt()` has no effect if the target process has already finished.

## Check for Understanding

What would happen if the manager called `self._worker.interrupt(...)` at
t=10, which is after `JOB_DURATION=10` would have elapsed?
Would the worker log "finish job" or "interrupted"?
