# A Minimal Framework

The minimal framework in `tutorial/01-minimal` includes an environment, processes, events, and timeouts.
Simulation time advances by executing scheduled callbacks,
not by real wall-clock time.

Processes are written as `async def` coroutines that `await` simulation events.

## Environment

The `Environment` owns the current simulation time (`now`)
and a priority queue of scheduled callbacks.
Calling:

```python
env.run()
```

executes callbacks until no events remain.
Callbacks are executed in (simulated) time order;
if two callbacks occur at the same time,
insertion order breaks ties.

## Process

A `Process` is an active entity in the simulation implemented as an `async` coroutine.
It is scheduled cooperatively by the `Environment`,
and resumes when `await`ed events complete.
The coroutine does *not* run continuously:
it only advances when an awaited event completes.

## Events

An `Event` represents something that will happen in the future.
Its key properties are:

1.  It may be `await`ed.
1.  It completes exactly once.
1.  It resumes all waiting processes.

Awaiting an event works because `Event.__await__` yields the event itself.
The process scheduler intercepts this and registers the process as a waiter.

## Timeouts

`Timeout` is the simplest event.
When a process calls:

```python
await env.timeout(5)
```

the framework creates a new `Timeout` event
that schedules a callback at `now` plus 5 clock ticks.
Timeouts are the only way to advance the simulated time in the system.

## How These Interact

1.  A `Process` starts running immediately when constructed
    (because its constructor calls `Environment.immediate`).

1.  It executes until it awaits an `Event`.

1.  That `Event` registers the `Process` as a waiter.

1.  When the `Event` succeeds,
    the `Process` is scheduled to resume execution.

As noted earlier,
simulated time advances only via scheduled callbacks.
