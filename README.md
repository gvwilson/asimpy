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

## Example: Timeout

The entire `Timeout` class is:

```python
class Timeout(Event):
    def __init__(self, env, delay):
        super().__init__(env)
        env.schedule(env.now + delay, lambda: self.succeed())
```

which simply asks the `Environment` to schedule `Event.succeed()` in the simulated future.

[docs]: https://gvwilson.github.io/asimpy
[examples]: https://gvwilson.github.io/asimpy/examples/
[package]: https://pypi.org/project/asimpy/
[repo]: https://github.com/gvwilson/asimpy
[simpy]: https://simpy.readthedocs.io/
