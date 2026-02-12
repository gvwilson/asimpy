# asimpy

A simple discrete event simulation framework in Python using `async`/`await`.

-   [Documentation][asimpy]
-   [Package][package]
-   [Repository][repo]

*Thanks to the creators of [SimPy][simpy] for inspiration.*

## Core Concepts

Discrete event simulation (DES) simulates systems in which events occur at discrete points in time.
The simulation maintains a virtual clock and executes events in chronological order.
Unlike real-time systems,
the simulation jumps directly from one event time to the next,
skipping empty intervals.
(Time steps are often referred to as "ticks".)

## Async/Await

Python's `async`/`await` syntax enables cooperative multitasking without threads.
Functions defined as `async def` return coroutine objects when called.
These coroutines can be paused at `await` points and later resumed.
More specifically,
when a coroutine executes `value = await expr`, it:

1.  yields the awaited object `expr` to its caller;
2.  suspends execution at that point;
3.  resumes later when `send(value)` is called on it; an thend
4.  returns the value passed to `send()` as the result of the `await` expression
    inside the resumed coroutine.

[asimpy][asimpy] uses this mechanism to pause and resume coroutines to simulate simultaneously execution.
This is similar to the `yield`-based mechanism used in [SimPy][simpy].

## `Environment`: Process and Event Management

The `Environment` class maintains the simulation state:

-  `_now` is the current simulated time.
-  `_pending` is a priority queue of callbacks waiting to be run in order of increasing time
    (so that the next one to run is at the front of the queue).

`Environment.schedule(time, callback)` adds a callback to the queue.
The `_Pending` dataclass used to store it includes a serial number
to ensure deterministic ordering when multiple events occur at the same time.

`Environment.run()` implements the main simulation loop:

1.  Extract the next pending event from the priority queue.
2.  If an `until` parameter is specified and the event time exceeds it, stop.
3.  Execute the callback.
4.  If the callback doesn't return `NO_TIME` and the event time is greater than the current simulated time,
    advance the clock.

The `NO_TIME` sentinel prevents time from advancing mistakenly when events are canceled.
This is explained in detail later.

## `Event`: the Synchronization Primitive

The `Event` class represents an action that will complete in the future.
It has four members:

-  `_triggered` indicates whether the event has completed.
-  `_cancelled` indicaets whether the event was cancelled.
-  `_value` is the event's result value.
-  `_waiters` is a list of processes waiting for this event to occur.

When `Event.succeed(value)` is called, it:

1.  sets `_triggered` to `True` to show that the event has completed;
2.  stores the value for later retrieval;
3.  calls `resume(value)` on all waiting processes; and
3.  clears the list of waiting processes.

The internal `Event._add_waiter(proc)` method handles three cases:

1.  If the event has already completed (i.e., if `_triggered` is `True`),
    it immediately calls `proc.resume(value)`.
2.  If the event has been canceled,
    it does nothing.
2.  Otherwise, it adds `proc` to the list of waiting processes.

Finally,
`Event` implements `__await__()`,
which Python calls automatically when it executes `await evt`.
`Event.__await__` yields `self` so that the awaiting process gets the event back.

## `Process`: Active Entities

`Process` is the base class for simulation processes.
(Unlike [SimPy][simpy], [asimpy][asimpy] uses a class rather than bare coroutines.)
When a `Process` is constructed, it:

1.  store a reference to the simulation environment;
2.  calls `init()` for subclass-specific setup
    (the default implementation of this method does nothing);
3.  create a coroutine by calling `run()`; and
4.  schedules immediate execution of `Process._loop()`.

The `_loop()` method drives coroutine execution:

1.  If an interrupt is pending, throw it into the coroutine via `throw()`.
2.  Otherwise, send the value into the coroutine via `send()`.
3.  Receive the yielded event.
4.  Register this process as a waiter on that event

When `StopIteration` is raised by the coroutine,
the process is marked as done.
If any other exception occurs,
the process is marked as done and the exception is re-raised.

**Note:** The word "process" can be confusing.
These are *not* operating system processes with their own memory and permissions.

### A Note on Scheduling

When an event completes it calls `proc.resume(value)` to schedules another iteration of `_loop()`
with the provided value.
This continues the coroutine past its `await` point.

### A Note on Interrupts

The interrupt mechanism sets `_interrupt` and schedules immediate execution of the process.
The next `_loop()` iteration throws the interrupt into the coroutine,
where it can be caught with `try`/`except`.
This is a bit clumsy,
but is the only way to inject exceptions into running coroutines.

**Note:**
A process can *only* be interrupted at an `await` point.
Exceptions *cannot* be raised from the outside at arbitrary points.

## `Timeout`: Waiting Until

A `Timeout` object schedules a callback at a future time.
`Timeout._fire()` method returns `NO_TIME` if the timeout has ben canceled,
which prevents canceled timeouts from accidentally advancing the simulation time.
Otherwise,
`Timeout._fire()` calls `succeed()` to trigger the event.

## `Queue`: Exchanging Data

`Queue` enables processes to exchange data.
It has two members:

-  `_items` is a list of items being passed between processes.
-  `_getters` is a list of processes waiting for items.

The invariant for `Queue` is that one or the other list must be empty,
i.e.,
if there are processes waiting then there aren't any items to take,
while if there are items waiting to be taken there aren't any waiting processes.

`Queue.put(item)` immediately calls `evt.succeed(item)` if a process is waiting
to pass that item to the waiting process
(which is stored in the event).
Otherwise,
the item is appended to `queue._items`.
`put()` is an `async` operation that returns `True` if the item was added
and `False` if it was not (e.g., because the queue is at capacity).

`Queue.get()` is a bit more complicated.
If the queue has items,
`queue.get()` creates an event that immediately succeeds with the first item.
If the queue is empty,
the call creates an event and adds the caller to the list of processes waiting to get items.

The complication is that if there *is* an item to get,
`queue.get()` sets the `_on_cancel` callback of the event to handles cancellation
by returning the item taken to the front of the queue.

If the `priority` constructor parameter is `True`,
the queue uses `insort` operations to maintain ordering,
which means items must be comparable (i.e., must implement `__lt__`).
`get()` returns the minimum element;
`put()` adds an element and potentially satisfies a waiting getter.

Queues allow creators to specify a maximum capacity.
The `discard` constructor parameter (default `True`) controls what happens
when someone attempts to `put` an item into a full queue.
If `discard` is `True`, a FIFO queue silently drops the new item,
while a priority queue adds the item and then drops the lowest-priority item.
If `discard` is `False`, the `put` call blocks until a `get` frees space in the queue.
When `max_capacity` is `None`, `discard` has no effect.

## `Resource`: Capacity-Limited Sharing

The `Resource` class simulates a shared resource with limited capacity.
It has three members:

-  `capacity` is the maximum number of concurrent users.
-  `_count` is the current number of users.
-  `_waiters` is a list of processes waiting for the resource to be available.

If the resource is below capacity when `res.acquire()` is called,
it calls increments the internal count and immediately succeeds.
Otherwise,
it adds the caller to the list of waiting processes.
Similarly,
`res.release()` decrements the count and then checks the list of waiting processes.
If there are any,
it calls `evt.succeed()` for the event representing the first waiting process.

`Resource.acquire` depends on internal methods
`Resource._acquire_available` and `Resource._acquire_unavailable`,
both of which set the `_on_cancel` callback of the event they create
to restore the counter to its original state
or remove the event marking a waiting process.

Finally,
the context manager protocol methods `__aenter__` and `__aexit__`
allows processes to use `async with res`
to acquire and release a resource in a block.

## `Barrier`: Synchronizing Multiple Processes

A `Barrier` holds multiple processes until they are explicitly released,
i.e.,
it allows the simulation to synchronize multiple processes.

-  `wait()` creates an event and adds it to the list of waiters.
-  `release()` calls `succeed()` on all waiting events and clears the list.

## AllOf: Waiting for Multiple Events

`AllOf` and `FirstOf` are the most complicated parts of [asimpy][asimpy],
and the reason that parts such as cancellation management exist.
`AllOf` succeeds when all provided events complete.
It:

1.  converts each input to an event (discussed later);
2.  registers an `_AllOfWatcher` on each of those events;
3.  accumulates results in `_results` dictionary; and
4.  succeeds when all results collected.

Each watcher calls `_child_done(key, value)` when its event completes.
This stores the result and checks if all events are done.

### A Note on Interface

A process calls `AllOf` like this:

```python
await AllOf(self._env, a=self.timeout(5), b=self.timeout(10))
```

The eventual result is a dictionary in which
the name of the events are keys and the results of the events are values;
in this case,
the keys will be `"a"` and `"b"`.
This gives callers an easy way to keep track of events,
though it *doesn't* support waiting on all events in a list.

`AllOf`'s interface would be tidier
if it didn't require the simulation environment as its first argument.
However,
removing it made the implementation significantly more complicated.

## FirstOf: Racing Multiple Events

`FirstOf` succeeds as soon as *any* of the provided events succeeds,
and then cancels all of the other events.
To do this, it:

1.  converts each input to an event;
2.  registers a `_FirstOfWatcher` on each;
3.  on first completion, cancels all other events; and
4.  succeeds with a `(key, value)` to identify the winning event.

`FirstOf`'s `_done` flag prevents multiple completions.
When `_child_done()` is called,
it checks this flag,
cancels other waiters,
and succeeds.

## Control Flow Example

Consider a process that waits 5 ticks:

```python
class Waiter(Process):
    async def run(self):
        await self.timeout(5)
        print("done")
```

When it executes:

1.  Construction calls `__init__()`,
    which creates a coroutine by calling `run()`
    and immediately schedules `_loop()`.
1.  The first `_loop()` calls `send(None)` to the coroutine,
    which executes to the `await`
    and yields a `Timeout` event.
1.  `_loop()` registers this process as a waiter on the timeout event.
1.  The timeout schedules a callback to run at time 5.
1.  The environment takes the event from its `_pending` queue and updates the simulated time to 5.
1.  The environment runs the callback, which calls `succeed()` on the timeout.
1.  The timeout calls `resume()` on the process.
1.  `resume()` schedules an immediate call to `_loop()` with the value `None`.
1.  `_loop()` calls `send(None)` on the coroutine,
    causing it to advance past the `await`.
1.  The process prints `"done"` and raises a `StopIteration` exception.
1.  The process is marked as done.
1.  Since there are no other events in the pending queue, the environment ends the simulation.

## A Note on Coroutine Adaptation

The `ensure_event()` function handles both `Event` objects and bare coroutines.
For coroutines, it creates a `_Runner` process that `await`s the coroutine
and then calls `succeed()` on an event with the result.
This allows `AllOf` and `FirstOf` to accept both events and coroutines.

`AllOf` and `FirstOf` must accept coroutines in addition to events
because of the way Python's `async`/`await` syntax works
and what users naturally write.
In the statement:

```python
await AllOf(env, a=queue.get(), b=resource.acquire())
```

the expressions `queue.get()` and `resource.acquire()` are calls to `async def` functions.
In Python,
calling an async function *does not execute it.
Instead, it returns a coroutine object.
If `AllOf` couldn't accept coroutines directly,
this code would fail because it expects `Event`s.

If `AllOf` only accepted events, users would need to write:

```python
# Manually create events
evt_a = Event(env)
evt_b = Event(env)

# Manually create runners
_Runner(env, evt_a, queue.get())
_Runner(env, evt_b, resource.acquire())

# Now use the events
await AllOf(env, a=evt_a, b=evt_b)
```

This is verbose and exposes internal implementation details.

## Things I Learned the Hard Way

### Requirements for Correctness

`Event` waiter notification must occur before clearing the list.
:   If the list were cleared first, waiters couldn't be resumed.

The `_Pending` serial number is necessary.
:   Heap operations require total ordering.
    Without this value,
    events occurring at the same time wouldn't be deterministically ordered,
    which would make simulations irreproducible.

Cancelled events must not advance time.
:   The `NO_TIME` sentinel prevents this.
    Without it,
    cancelled timeouts create gaps in the simulation timeline.

Process interrupt checking must occur before coroutine sends.
:   This ensures interrupts are handled immediately
    rather than being delayed until the next event.

Queue cancellation handlers must remove items or waiters.
:   Without this,
    cancelled `get`s leave processes in the waiters list indefinitely,
    and cancelled items disappear from the queue.

Resource cancellation handlers must adjust state.
:   Without them,
    cancelled `acquire`s permanently reduce available capacity or leave ghost waiters.

`AllOf` must track completion.
:   Without checking if all events are done, it succeeds prematurely.

`FirstOf` must cancel losing events.
:   Otherwise,
    those events remain active and can run later.

### Why Not Just Use Coroutines?

[SimPy][simpy] uses bare coroutines.
[asimpy][asimpy] uses `Event` as the internal primitive for several reasons.

Events can be triggered externally.
:   A `Timeout` schedules a callback that later calls `succeed()`.
    A coroutine cannot be "succeeded" from outside: it must run to completion.

Events support multiple waiters.
:   Multiple processes can `await` the same event.
    A coroutine can only be awaited once.

Events decouple triggering from waiting.
:   The thing that creates an event (like `Timeout.__init__()`)
    is separate from the thing that waits for it.
    With coroutines, creation and execution are more tightly coupled.

### `Event.__await__`

`Event.__await__` is defined as:

```python
def __await__(self):
    value = yield self
    return value
```

This appears redundant but each part serves a specific purpose in the coroutine protocol.

When a coroutine executes `await event`,
Python calls `event.__await__()`,
which must return an iterator.
The `yield self` statement:

1.  makes `__await__()` a generator function,
    so it returns a generator (which is a kind of iterator).
2.  Yields the `Event` object itself up to the `Process`'s `_loop()` method.

The `Process` needs the `Event` object so it can call `_add_waiter()` on it:

```python
def _loop(self, value=None):
    # ...
    yielded = self._coro.send(value)  # This receives the Event
    yielded._add_waiter(self)         # Register as waiter
```

Without `yield self`, the `Process` wouldn't know which event to register on.

The `value = yield self` statement captures what gets sent back into the generator.
When the event completes:

1.  `Event` calls `proc.resume(value)` .
2.  `Process` calls `self._loop(value)`.
3.  `_loop` calls `self._coro.send(value)`.
4.  This resumes the generator, making `yield self` return `value`.

The assignment therefore captures the event's result value.

### Why Return Value

The `return value` statement makes that result available to the code that wrote `await event`.
When a generator returns (via `return` or falling off the end)
Python raises `StopIteration` with the return value as an attribute.
The `async`/`await` machinery extracts this and provides it as the result of the `await` expression,
So when a user writes:

```python
result = await queue.get()
```

the flow is:

1.  `queue.get()` creates and returns an `Event`.
1.  `await` calls `Event.__await__()` which yields the `Event` object.
1.  `Process._loop()` receives the `Event` and registers itself as a waiter.
1.  Later, the queue calls `event.succeed(item)`.
1.  `Event` calls `process.resume(item)`.
1.  `Process` calls `coro.send(item)`.
1.  The generator resumes, and `yield self` evaluates to `item`.
1.  The generator executes `return item`.
1.  `StopIteration(item)` is raised.
1.  The `async` machinery catches this and makes `await` evaluate to `item`.

None of the simpler alternatives would work:

- `yield self` alone (no return): the await expression would evaluate to `None`.
- `return self` (no yield): not a generator, so it violates the iterator protocol.
- `yield value` then `return value`: the first yield wouldn't provide the `Event` object to the `Process`.

[asimpy]: https://asimpy.readthedocs.io/
[package]: https://pypi.org/project/asimpy/
[repo]: https://github.com/gvwilson/asimpy
[simpy]: https://simpy.readthedocs.io/
