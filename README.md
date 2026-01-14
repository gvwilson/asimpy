# asimpy

A simple discrete event simulation framework in Python using `async`/`await`.

-   [Documentation][docs]
-   [Package][package]
-   [Repository][repo]
-   [Examples][examples]

*Thanks to the creators of [SimPy][simpy] for inspiration.*

## What This Is

This discrete-event simulation framework uses Python's `async`/`await` without `asyncio`.
Key concepts include:

-   Simulation time is virtual, not wall-clock time.
-   Processes are active entities (customers, producers, actors).
-   Events are things that happen at specific simulation times.
-   `await` is used to pause a process until an event occurs.
-   A single-threaded event loop (the `Environment` class) advances simulated time and resumes processes.

The result feels like writing synchronous code, but executes deterministically.

## The Environment

The `Environment` class is the core of `asimpy`.
It store upcoming events in a heap that keeps entries ordered by (simulated) time.
`env.run()` repeatedly pops the earliest scheduled callback,
advances `env._now` to that time,
and runs the callback.

> The key idea is that *nothing runs until the environment schedules it*.

## Events

An `Event` represents something that may happen later (similar to an `asyncio` `Future`).
When a process runs:

```python
value = await some_event
```

the following happens:

1.  `Event.__await__()` yields the event object.
1.  The process is suspended.
1.  The process is registered as a waiter on that event.

When `event.succeed(value)` is called:

1.  The event is marked as triggered.
1.  All waiting processes are resumed.
1.  Each of those processes receives `value` as the result of `await`.

One way to understand `Event` is to look at the purpose of its key attributes.

### `_triggered`

The Boolean `_triggered` indicates whether this event has already successfully occurred.
It is initially `False`,
and is set to `True` when `evt.succeed(value)` is called.
If the event has been triggered before,
and some process wants to wait on it later,
that process is immediately resumed with the store `_value`.
This prevents lost or duplicated notifications.

```python
def succeed(self, value=None):
    if self._triggered or self._cancelled:
        return
    self._triggered = True
    self._value = value
    for proc in self._waiters:
        proc._resume(value)
    self._waiters.clear()
```

### `_cancelled` and `_on_cancel`

The Boolean `_cancelled` indicates whether the event was aborted before it could succeed.
It is also initially `False`,
and is used in both `succeed()` (shown above) and in `cancel()`:

```python
def cancel(self):
    if self._triggered or self._cancelled:
        return
    self._cancelled = True
    self._waiters.clear()
    if self._on_cancel:
        self._on_cancel()
```

If a cancellation callback has been registered with the event,
the callback is executed to do resource cleanup.
For example,
suppose a program is using `FirstOf` to wait until an item is available
on one or the other of two queues.
If both queues become ready at the same simulated time,
the program might take one item from both queues
when it should instead take an item from one or the other queue.
To clean this up,
`Queue.get()` registers a callback that puts an item back at the front of the queue
to prevent incorrect over-consumption of items:

```python
evt._on_cancel = lambda: self._items.insert(0, item)
```

### `_value`

When `evt.succeed(value)` is called,
the value passed in is saved as `evt._value`.
Any process resuming from `await event` receives this value:

```python
class Event:
    def __await__(self):
        value = yield self
        return value
```

This is how the framework passes results between processes:
for example,
the value of a `Queue.get()` event is the item retrieved from the queue.

### `_waiters`

`_waiters` is a list of processes waiting for the event to complete.
When a process `await`s an event,
it is added to the list by the internal method `_add_waiter()`.
If the event has already been triggered,
`_add_waiter` immediately resumes the process:

```python
def _add_waiter(self, proc):
    if self._triggered:
        proc._resume(self._value)
    elif not self._cancelled:
        self._waiters.append(proc)
```

When `succeed()` is called,
every process in `_waiters` is resumed and `_waiters` is cleared.
When `cancel()` is called, `_waiters` is cleared without resuming any process.

## Processes

The `Process` class wraps an `async def run()` coroutine.
When a `Process` is created,
its constructor called `self.run()` to create a coroutine
and then gives the `self._loop` callback to the `Enviroment`,
which schedules it to run.

`self._loop` drives the coroutine by executing:

```python
yielded = self._coro.send(value)
yielded._add_waiter(self)
```

1.  The coroutine runs until it hits `await`.
1.  The `await` yields an `Event`.
1.  The process registers itself as waiting on that event.
1.  Control returns to the environment.

When the event fires, it calls:

```python
proc._resume(value)
```

which schedules `_loop(value)` again.

## Example: `Timeout`

The entire `Timeout` class is:

```python
class Timeout(Event):
    def __init__(self, env, delay):
        super().__init__(env)
        env.schedule(env.now + delay, lambda: self.succeed())
```

which simply asks the `Environment` to schedule `Event.succeed()` in the simulated future.

## Example: `FirstOf`

Suppose the queue `q1` contains `"A"` and the `q2` contains `"B"`,
and a process then waits for a value from either queue with:

```python
item = await FirstOf(env, a=q1.get(), b=q2.get())
```

The sequence of events is:

| Action / Event                            | Queue State        | Event State                             | Process / Waiters                                | Notes                                                     |
| ----------------------------------------- | ------------------ | --------------------------------------- | ------------------------------------------------ | --------------------------------------------------------- |
| `Tester` starts                           | q1=["A"], q2=["B"] | evt_a & evt_b created                   | `_waiters` in evt_a and evt_b = [Tester]         | `FirstOf` yields to environment                           |
| `q1.get()` removes "A"                    | q1=[], q2=["B"]    | evt_a._value=None, _triggered=False     | evt_a._waiters=[FirstOfWatcher]                  | _on_cancel set to re-insert "A" if cancelled              |
| `q2.get()` removes "B"                    | q1=[], q2=[]       | evt_b._value=None, _triggered=False     | evt_b._waiters=[FirstOfWatcher]                  | _on_cancel set to re-insert "B" if cancelled              |
| Environment immediately triggers evt_a    | q1=[], q2=[]       | evt_a._value="A", _triggered=True       | _waiters processed: FirstOf._child_done() called | This is the winner                                        |
| FirstOf `_child_done()` sets `_done=True` | q1=[], q2=[]       | _done=True                              | _events = {a: evt_a, b: evt_b}                   | Notifies all losing events to cancel                      |
| evt_b.cancel() called (loser)             | q1=[], q2=[]       | evt_b._cancelled=True                   | _waiters cleared                                 | _on_cancel triggers: inserts "B" back at front of q2      |
| `_on_cancel` restores item                | q1=[], q2=["B"]    | evt_b._triggered=False, _cancelled=True | _waiters cleared                                 | Queue order preserved                                     |
| FirstOf succeeds with winner              | q1=[], q2=["B"]    | _value=("a","A"), _triggered=True       | Processes waiting on FirstOf resumed             | `Tester` receives ("a","A")                               |
| `Tester` continues execution              | q1=[], q2=["B"]    | -                                       | -                                                | Remaining queue items untouched; correct order guaranteed |

[docs]: https://gvwilson.github.io/asimpy
[examples]: https://gvwilson.github.io/asimpy/examples/
[package]: https://pypi.org/project/asimpy/
[repo]: https://github.com/gvwilson/asimpy
[simpy]: https://simpy.readthedocs.io/
