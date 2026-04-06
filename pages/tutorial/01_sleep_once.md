# Sleep Once

A step-by-step trace of what happens when the example runs, for newcomers who
want to understand asimpy's internals.  Each column is a key actor; rows flow
from top to bottom in execution order.

## Source and Output

```python
--8<-- "examples/01_sleep_once.py"
```

```text
--8<-- "output/01_sleep_once.txt"
```

## Execution Trace

| Step | Entity | Action |
| ---: | :----- | :----- |
| 1 | `env.now` | 0 |
|   | `env.ready` | `[]` |
|   | `env.heap` | `[]` |
|   | `Environment.run()` | `Environment()` created |
|   | `Sleeper._loop()` | — |
|   | `Timeout` event | — |
|   | `Sleeper.run()` coroutine | — |
| 2 | `env.now` | 0 |
|   | `env.ready` | `[_loop]` |
|   | `env.heap` | `[]` |
|   | `Environment.run()` | `Sleeper(env)` is constructed; `Process.__init__` calls `env.immediate(self._loop)`, queuing `_loop` in `_ready` |
|   | `Sleeper._loop()` | Scheduled but not yet called |
|   | `Timeout` event | — |
|   | `Sleeper.run()` coroutine | `self.run()` creates the coroutine object; execution has not started |
| 3 | `env.now` | 0 |
|   | `env.ready` | `[]` |
|   | `env.heap` | `[]` |
|   | `Environment.run()` | `env.run()` begins; inner loop pops `_loop` from `_ready` and calls it |
|   | `Sleeper._loop()` | `_loop(None)` invoked; sets `_started = True`; calls `self._coro.send(None)` to start the coroutine |
|   | `Timeout` event | — |
|   | `Sleeper.run()` coroutine | Coroutine begins; prints `"t=00: start"` |
| 4 | `env.now` | 0 |
|   | `env.ready` | `[]` |
|   | `env.heap` | `[(5, _fire)]` |
|   | `Environment.run()` | — |
|   | `Sleeper._loop()` | Still inside `send()`; waiting for coroutine to yield |
|   | `Timeout` event | `Timeout(env, 5)` created by `self.timeout(5)`; constructor calls `env.schedule(5, self._fire)`, pushing onto the heap |
|   | `Sleeper.run()` coroutine | `await self.timeout(5)`: `__await__` does `yield timeout_obj`, suspending and handing the `Timeout` back to `_loop` |
| 5 | `env.now` | 0 |
|   | `env.ready` | `[]` |
|   | `env.heap` | `[(5, _fire)]` |
|   | `Environment.run()` | — |
|   | `Sleeper._loop()` | Receives `yielded = timeout_obj`; checks `timeout_obj._value is _PENDING` (True); calls `timeout_obj._add_waiter(self.resume)` then `break`s |
|   | `Timeout` event | `_waiters = [sleeper.resume]` |
|   | `Sleeper.run()` coroutine | Parked at `await` |
| 6 | `env.now` | 0 → 5 |
|   | `env.ready` | `[_loop]` |
|   | `env.heap` | `[]` |
|   | `Environment.run()` | `_ready` is empty; pops `(5, _fire)` from heap; calls `_fire()`; advances `_now = 5` |
|   | `Sleeper._loop()` | — |
|   | `Timeout` event | `_fire()` calls `succeed()`; iterates `_waiters`, calls `sleeper.resume(None)`, which calls `env.immediate(partial(_loop, None))` |
|   | `Sleeper.run()` coroutine | Still suspended |
| 7 | `env.now` | 5 |
|   | `env.ready` | `[]` |
|   | `env.heap` | `[]` |
|   | `Environment.run()` | Drains `_ready`: pops and calls `_loop(None)` |
|   | `Sleeper._loop()` | `_loop(None)` invoked; calls `self._coro.send(None)` to resume the coroutine |
|   | `Timeout` event | `_value = None`, `_waiters = []` |
|   | `Sleeper.run()` coroutine | `yield` in `__await__` returns `None`; `await` completes; prints `"t=05: end"`; coroutine returns |
| 8 | `env.now` | 5 |
|   | `env.ready` | `[]` |
|   | `env.heap` | `[]` |
|   | `Environment.run()` | `_ready` and `_heap` both empty; outer loop `break`s; `run()` returns |
|   | `Sleeper._loop()` | Catches `StopIteration`; sets `_done = True` |
|   | `Timeout` event | — |
|   | `Sleeper.run()` coroutine | Finished |

## Key Points

1.  `env.immediate` vs `env.schedule`: `immediate` pushes onto
    `_ready` (no clock advance); `schedule` pushes onto `_heap`
    (future time).  The clock only advances when popping from the
    heap.

2.  The coroutine protocol: `yield timeout_obj` in `Event.__await__`
    is what suspends the process.  Python's `send()` / `throw()` drive
    it from `_loop`.

3.  Waiter registration: `_add_waiter(self.resume)` is how `Timeout`
    knows which process to wake up when it fires.  There can be
    multiple waiters.

4.  Tight loop: if a yielded event is already triggered when `_loop`
    checks it, `_loop` immediately calls `send()` again without going
    through the heap.  This is the fast path for pre-satisfied events.

## Check for Understanding

In step 4, `self.timeout(5)` returns a `Timeout` object.
What two things does the `Timeout` constructor do, and why are they separate concerns?
