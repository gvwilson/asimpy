# asimpy

asimpy is a discrete event simulation library using async/await. The core
insight driving this design is that all primitives return `Event` objects
rather than coroutines. This single decision eliminates the `_Runner` /
`_ensure_event` complexity in asimpy and allows `AllOf` / `FirstOf` to work
with any primitive without wrapping.

## What We Learned from simpy and asimpy

### simpy (generator-based)

- Clean priority-heap scheduler: `(time, priority, serial, event)`.
- `Event` holds a `callbacks` list; triggered events schedule themselves and
  call all callbacks.
- `Process` wraps a generator; `_resume` is the callback registered on each
  event the generator yields.
- `BoundClass` descriptor trick binds resource event constructors to the
  environment at startup for performance; this adds conceptual overhead for
  little gain in a modern Python library.
- `BaseResource` + `_do_put` / `_do_get` template pattern is reusable but
  forces all resources into a single put/get mental model.
- `Condition` / `AllOf` / `AnyOf` count callbacks to a shared counter, then
  trigger when the condition is met; clean but tied to the generator API.

### asimpy (async/await-based)

**Strengths to keep:**
- Separate `_ready` deque (current-time callbacks) and `_heap` (future events)
  avoids priority inversion at time zero and keeps the clock from advancing
  for zero-delay work.
- `_PENDING` / `_CANCELLED` sentinel values in `Event._value` are cheaper
  than boolean flags and make state transitions atomic.
- Tight-loop optimisation in `Process._loop`: if the yielded event is already
  triggered, resume immediately without a heap round-trip. Critical for
  performance.
- Lazy deletion of cancelled waiters in queues and resources; avoids O(n)
  scans.
- `Interrupt` thrown into the coroutine; clean exception-based API.
- `Barrier` is minimal and correct.

**Complexity to eliminate:**
- `Queue.get()` and `Queue.put()` are `async def` coroutines, not plain
  methods that return `Event` objects. This means `AllOf` / `FirstOf` must
  wrap arbitrary coroutines in `_Runner` subprocesses via `_ensure_event`,
  adding ~50 lines of infrastructure. If all primitives return `Event`
  objects instead, `AllOf` / `FirstOf` never need to spawn processes.
- `_on_cancel` callbacks on individual events add per-event overhead and
  require careful lifecycle management. Lazy deletion in the waiter lists
  achieves the same result more simply.
- `PreemptiveResource` is a complex advanced feature; defer to a later phase.

### calls/sim.py awkward pattern

Agents sleep on `timeout(float("inf"))` and are woken via `interrupt`. This
is fragile (any other interrupt looks the same) and semantically wrong (an
interrupt is an error, not a normal wakeup). The fix: expose `Event` directly
so an agent can `await` a named `Event` that a client triggers with
`.succeed(value)`.

## Design Decisions

### D1 — All primitives return `Event`, not coroutines

`queue.get()`, `queue.put(item)`, `resource.acquire()`, `store.get()`, etc.
are all plain (non-async) methods that return an `Event`. The caller does
`item = await queue.get()`. This means:

- No `_Runner` / `_ensure_event` needed anywhere.
- `AllOf(env, a=queue.get(), b=store.get())` just works.
- Pre-triggered events are returned for immediately-satisfied requests; the
  tight loop in `Process._loop` resumes without a heap round-trip.

### D2 — Environment keeps two queues

Same as asimpy: `_ready: deque` for current-time callbacks and `_heap` for
future events. The clock only advances when popping from `_heap`.

### D3 — Event state via sentinels

`_PENDING`, `_CANCELLED` (objects), and any other value = triggered with that
value. `Event.succeed(value)` sets `_value`, drains `_waiters`. `Event.fail(exc)`
sets `_value` to the exception; the process's `_loop` re-raises it. `Event.cancel()`
sets `_value = _CANCELLED` and discards waiters.

### D4 — Lazy deletion in all waiter lists, plus `_on_cancel` for consumed resources

When a pending event is cancelled, its sentinel value tells any queue /
resource / barrier that inspects it to skip and discard it. No additional
hooks are needed for this case.

However, when a pre-triggered get event (item already removed from a
resource) is cancelled by `FirstOf`, lazy deletion alone is insufficient —
the item has already been consumed. `Event.cancel()` therefore calls
`_on_cancel(old_value)` even for triggered events (see "FirstOf and resource
loss" in the Internal Mechanics section). Resource get methods set
`_on_cancel` before calling `succeed()` so the callback is always available.

### D5 — Process uses _loop / resume from asimpy (unchanged)

The `_loop` method is the only complex piece; it is already well-designed in
asimpy. asimpy keeps it verbatim (minus the `_on_cancel` handling). `resume`
uses `functools.partial` for a C-level callable, as in asimpy.

### D6 — Explicit Event for sleep/wake (req 8)

Instead of `timeout(inf) + interrupt`, a process creates a plain `Event`
and awaits it. It can put the event (or itself paired with the event) in a
`Store`. Another process gets the event and calls `.succeed(value)`. This is
the natural async/await idiom and requires no new primitives.

## Class-by-Class Specification

### `Environment` (`core.py`)

```
Attributes:
    now: float          current simulation time (read-only)
    active_process      the Process currently executing, or None

Methods:
    run(until=None)     run until no events remain, or until time/event
    immediate(cb)       schedule cb at current time (internal)
    schedule(time, cb)  schedule cb at future time (internal)
    timeout(delay)      convenience: return Timeout(self, delay)
```

- `run` loop:
  1. Drain `_ready` completely (zero-delay work at current time).
  2. If `_heap` is empty, stop.
  3. Peek at earliest future time; if `until` exceeded, stop.
  4. Pop and call the callback; advance clock only if the time is new.

### `Event` (`core.py`)

```
__slots__ = ("_env", "_value", "_waiters")

State sentinels:
    _PENDING    = object()   # not yet triggered
    _CANCELLED  = object()   # cancelled; waiters discarded

Properties (derived from _value):
    triggered: bool     _value is not _PENDING and not _CANCELLED
    cancelled: bool     _value is _CANCELLED

Methods:
    succeed(value=None)     trigger with value; call all _waiters
    fail(exc: Exception)    trigger with exception (stored as value)
    cancel()                cancel; discard waiters
    _add_waiter(cb)         if triggered: call cb immediately;
                            if pending: append; if cancelled: ignore
    __await__()             yield self; return received value;
                            if value is Exception, raise it
```

The `__await__` protocol: `value = yield self`. In `Process._loop`, if the
value is an `Exception` instance, it is raised (implements `fail`).

### `Interrupt` (`core.py`)

```python
class Interrupt(Exception):
    def __init__(self, cause):
        self.cause = cause
```

Thrown into the process coroutine by `Process.interrupt(cause)`. The process
can catch it with `except Interrupt as e: ... e.cause ...`.

### `Timeout` (`core.py`)

Subclass of `Event`. `__init__(env, delay)` validates `delay >= 0`, then
calls `env.schedule(env.now + delay, self._fire)`. `_fire` calls
`self.succeed()` unless already cancelled (returns a `_NO_TIME` sentinel to
tell `run` not to advance the clock for phantom events, matching asimpy).

### `Process` (`core.py`)

Abstract base class.

```
Constructor: __init__(env, *args, **kwargs)
    - stores env
    - calls self.init(*args, **kwargs)      # subclass setup hook
    - creates coroutine: self._coro = self.run()
    - schedules self._loop via env.immediate

Properties:
    now     shortcut to env.now
    done    True after run() returns or raises

Abstract method:
    async def run(self)     subclass implements behaviour

Optional override:
    def init(self, *args, **kwargs)    called before coroutine creation

Instance methods:
    interrupt(cause)        if not done: set self._interrupt = Interrupt(cause);
                            schedule self._loop via env.immediate
    timeout(delay)          return env.timeout(delay)   # convenience
    _loop(value=None)       internal: drives the coroutine (see below)
    resume(value=None)      schedules partial(self._loop, value) via immediate
```

`_loop` (unchanged from asimpy):
1. Set `env.active_process = self`.
2. If `_interrupt` is pending and coroutine started: cancel `_current_event`,
   clear `_interrupt`, call `coro.throw(interrupt)`.
3. Else: call `coro.send(value)`.
4. Tight loop: if the yielded event is already triggered, loop again with
   its value without going through the heap.
5. Otherwise register `self.resume` as a waiter on the event; break.
6. On `StopIteration`: mark done.
7. On `Exception`: mark done, re-raise.
8. Finally: `env.active_process = None`.

### `Queue` (`queue.py`)

```
class QueueEmpty(Exception): pass
class QueueFull(Exception): pass

class Queue:
    __init__(env, capacity=None)    capacity=None means unlimited

    # Blocking (return Event)
    get() -> Event          value = item when dequeued
    put(item) -> Event      value = True when enqueued

    # Non-blocking (raise on failure)
    try_get() -> item       raises QueueEmpty if empty
    try_put(item)           raises QueueFull if full

    # Introspection
    is_empty() -> bool
    is_full() -> bool
    size() -> int
```

Internal state: `_items: deque`, `_getters: deque[Event]`,
`_putters: deque[tuple[Event, item]]`. Lazy deletion skips cancelled events.

`get()` logic:
- If `_items` non-empty: pop item, promote one non-cancelled putter (add its
  item to `_items`, call `putter_evt.succeed(True)`), create a pre-triggered
  `Event(value=item)`, return it.
- Else: create `Event`, append to `_getters`, return it.

`put(item)` logic:
- While `_getters` has non-cancelled entries: deliver item directly via
  `getter_evt.succeed(item)`, return a pre-triggered `Event(value=True)`.
- If not full: add to `_items`, return a pre-triggered `Event(value=True)`.
- Else: create `Event`, append `(evt, item)` to `_putters`, return `evt`.

`try_get()`: if `_items` non-empty, pop and return; else raise `QueueEmpty`.
`try_put(item)`: if not full, add and return; else raise `QueueFull`.

Note: `try_get` and `try_put` do not trigger blocked waiters. If `try_put`
succeeds and there are blocked getters, they will be served on the next
`get()` call. This keeps the non-blocking path simple and avoids the need to
call environment callbacks from a synchronous context.

### `Container` (`container.py`)

Models a homogeneous resource (continuous or discrete amounts).

```
class ContainerEmpty(Exception): pass
class ContainerFull(Exception): pass

class Container:
    __init__(env, capacity=inf, init=0.0)
    level: float    current amount

    # Blocking
    get(amount) -> Event    value = amount when fulfilled
    put(amount) -> Event    value = amount when fulfilled

    # Non-blocking
    try_get(amount) -> float    raises ContainerEmpty if level < amount
    try_put(amount) -> float    raises ContainerFull if no space
```

Internal state: `_level: float`, `_getters: list[tuple[amount, Event]]`,
`_putters: list[tuple[amount, Event]]`.

`get(amount)` logic:
- If `_level >= amount`: subtract, try to promote putters, return
  pre-triggered event.
- Else: create event, append `(amount, evt)` to `_getters`, return event.

`put(amount)` logic:
- If `_level + amount <= capacity`: add, try to satisfy getters, return
  pre-triggered event.
- Else: create event, append `(amount, evt)` to `_putters`, return event.

After any state change, iterate the opposite waiter list (skipping cancelled)
to promote as many as possible. Use lazy deletion.

### `Store` (`store.py`)

Models a collection of heterogeneous objects.

```
class StoreEmpty(Exception): pass
class StoreFull(Exception): pass

class Store:
    __init__(env, capacity=inf)

    # Blocking
    get(filter=None) -> Event    value = item; filter is callable or None
    put(item) -> Event           value = True

    # Non-blocking
    try_get(filter=None) -> item    raises StoreEmpty
    try_put(item)                   raises StoreFull
```

Internal state: `_items: list`, `_getters: list[tuple[filter, Event]]`,
`_putters: list[tuple[item, Event]]`.

`get(filter)` logic:
- Scan `_items` for first item where `filter(item)` is True (or filter is
  None). If found: remove item, promote one non-cancelled putter, return
  pre-triggered event with item.
- Else: create event, append `(filter, evt)` to `_getters`, return event.

`put(item)` logic:
- If any non-cancelled getter whose filter matches item: deliver directly,
  return pre-triggered event.
- If not full: append item. Check if any pending getter now matches (scan
  `_getters`). Return pre-triggered event.
- Else: create event, append `(item, evt)` to `_putters`, return event.

Note on Store as sleep/wake primitive (req 8): a process creates an `Event`,
puts it in a Store, then awaits it. Another process gets the event from the
Store and calls `.succeed(value)`. This replaces the `timeout(inf) + interrupt`
pattern.

Example:
```python
class Worker(Process):
    async def run(self):
        while True:
            wakeup = Event(self.env)
            await store.put(wakeup)   # make self available
            value = await wakeup       # sleep until claimed and woken

class Dispatcher(Process):
    async def run(self):
        wakeup = await store.get()    # claim a waiting worker
        wakeup.succeed("do task X")   # wake it
```

### `Resource` (`resource.py`)

Models discrete shared capacity (slots).

```
class Resource:
    __init__(env, capacity=1)
    count: int      current number of users
    capacity: int

    acquire() -> Event    value = None; blocks if full
    try_acquire() -> bool returns True if acquired, False if not (no blocking)
    release()             synchronous; promotes one blocked waiter
```

`acquire()` logic:
- If `_count < capacity`: increment `_count`, return pre-triggered event.
- Else: create event, append to `_waiters`, return event.

`release()`:
- Decrement `_count`.
- Drain `_waiters` (lazy deletion) until one non-cancelled waiter found:
  increment `_count`, call `evt.succeed()`.

`try_acquire()`: if `_count < capacity`, increment and return True; else
return False (no exception, unlike Queue/Container/Store which raise).

Context manager protocol (`async with resource`): `__aenter__` awaits
`acquire()`; `__aexit__` calls `release()`.

### `Barrier` (`barrier.py`)

```
class Barrier:
    __init__(env)

    wait() -> Event    value = None; blocks until release()
    release()          triggers all currently-waiting events
```

`wait()`: create event, append to `_waiters`, return event.
`release()`: call `.succeed()` on all events in `_waiters`, then clear.

Note: Unlike asimpy, `wait()` returns an `Event` (not a coroutine). Usage:
`await barrier.wait()`.

### `AllOf` (`allof.py`)

Wait for all events to trigger.

```
class AllOf(Event):
    __init__(env, **events)    keyword args; each value must be an Event
```

Registers `_child_done(key, value)` as a waiter on each child event.
When all children have triggered, calls `self.succeed(results_dict)`.

No `_Runner` needed because all children are already `Event` instances.

`AllOf` is itself an `Event`, so it can be nested: `await AllOf(env, a=allof1, b=evt2)`.

Example:
```python
results = await AllOf(env, item=store.get(), slot=resource.acquire())
item = results["item"]
```

### `FirstOf` (`firstof.py`)

Wait for the first event to trigger.

```
class FirstOf(Event):
    __init__(env, **events)    keyword args; each value must be an Event
```

Registers `_child_done(key, value, winner_event)` on each child.
On first trigger: cancel all other events, call `self.succeed((key, value))`.
Subsequent calls to `_child_done` are ignored (`_finished` flag).

Cancellation propagates correctly via lazy deletion in Queue/Store/Resource
waiter lists; no `_on_cancel` callbacks needed.

Example:
```python
key, value = await FirstOf(env, timeout=env.timeout(10), item=queue.get())
if key == "timeout":
    ...  # queue was empty for 10 time units
else:
    ...  # got item before timeout
```

## Event Loop: Step-by-Step

```
env.run(until=T):
    while True:
        while _ready:               # drain all zero-delay work
            cb = _ready.popleft()
            cb()
        if not _heap:
            break
        next_time = _heap[0][0]
        if until is not None and next_time > until:
            break
        _, _, cb = heappop(_heap)
        result = cb()               # cb is Timeout._fire or similar
        if result is not _NO_TIME and next_time > _now:
            _now = next_time
```

The `_NO_TIME` sentinel (from `Timeout._fire` when cancelled) prevents the
clock from advancing for phantom events. This is the same as asimpy.

## Internal Mechanics

### `_loop` and `resume`

#### The problem they solve

Python's `asyncio` has its own event loop, incompatible with newsim's scheduler.
Newsim drives its coroutines manually via `coro.send()` and `coro.throw()`.

When a process does `await some_event`, Python's `Event.__await__` executes
`value = yield self`, which suspends the coroutine and returns `some_event`
to whoever last called `coro.send(value)`. That caller is `_loop`.

#### Step-by-step execution

```
Process.__init__:
    self._coro = self.run()       # coroutine object, not yet started
    env.immediate(self._loop)     # schedule first _loop call at time 0
```

**First call to `_loop(value=None)`:**
1. `env.active_process = self`
2. `yielded = self._coro.send(None)` — starts the coroutine; runs until the
   first `await event`, which yields `event` back. `yielded` is that Event.
3. Check `yielded._value`:
   - **Already triggered** (not `_PENDING`, not `_CANCELLED`):
     set `value = yielded._value` and loop back to step 2. The coroutine
     resumes immediately — no heap round-trip.
   - **Still pending**: call `yielded._add_waiter(self.resume)` and `break`.
4. `env.active_process = None`

**When the event fires (`event.succeed(item)`):**
- `self.resume(item)` is called (it was a waiter).
- `resume` calls `env.immediate(partial(self._loop, item))`.
- Next tick: `_loop(value=item)` → `coro.send(item)` → coroutine resumes;
  `item` is the result of the `await`.

#### The tight-loop optimisation

Without it, every `await` — even on an already-satisfied event — pays a
`heappush` + `heappop`. With it, a chain of pre-triggered events (e.g.
`a = await queue.get(); b = await queue.get()` when the queue has multiple
items) runs entirely inside `_loop`'s `while True`, at zero heap cost.

#### Interrupts

`process.interrupt(cause)`:
1. Sets `self._interrupt = Interrupt(cause)`.
2. Calls `env.immediate(self._loop)`.

Next time `_loop` runs:
1. Sees `_interrupt is not None` and `_started is True` (throws into an
   unstarted coroutine bypass its `try/except` blocks — `_started` prevents
   this).
2. Cancels `_current_event` (the parked event) so it cannot call `resume`
   later with a stale value.
3. Calls `self._coro.throw(self._interrupt)`, raising `Interrupt(cause)`
   inside the coroutine at its current `await`.
4. The coroutine catches it with `except Interrupt as e: ...`.

### FirstOf and resource loss

#### Normal case: one event still pending

When `FirstOf` chooses winner `a`, `_child_done` does:

```python
self._finished = True
for evt in self._events.values():
    if evt is not winner:
        evt.cancel()
self.succeed((key, value))
```

For a **pending** `evt_b` from `queue_b.get()`:
- The item has not been removed yet — it is still in `queue_b._items`.
- `evt_b.cancel()` sets `evt_b._value = _CANCELLED`.
- Lazy deletion in `queue_b.put()` skips `evt_b` when scanning `_getters`.
  The item stays in the queue. Nothing is lost.

#### The bug: two pre-triggered events

`Event.cancel()` naively implemented as `if _value is not _PENDING: return`
is wrong when both events are pre-triggered.

Scenario: both `queue_a` and `queue_b` have items.

```python
key, val = await FirstOf(env, a=queue_a.get(), b=queue_b.get())
```

`queue_a.get()` pops `item_a` and returns a pre-triggered `evt_a`.
`queue_b.get()` pops `item_b` and returns a pre-triggered `evt_b`.
`FirstOf.__init__` calls `_add_waiter` on `evt_a` first → `_child_done("a")`
fires immediately → `_finished = True`, cancel `evt_b`. But `evt_b` is
already triggered, so the naive `cancel()` is a no-op. `item_b` is gone from
`queue_b` and nobody receives it. **Lost.**

#### The fix: `cancel()` fires `_on_cancel` even for triggered events

```python
def cancel(self) -> None:
    if self._value is _CANCELLED:
        return          # already cancelled; don't fire twice
    old_value = self._value
    self._value = _CANCELLED
    self._waiters = []
    if self._on_cancel is not None:
        self._on_cancel(old_value)   # old_value may be _PENDING or a real value
```

All resource-consuming `get()` methods set `_on_cancel` before calling
`succeed()`:

```python
# Queue.get() pre-triggered path
evt._on_cancel = lambda v: self._items.appendleft(v)
evt.succeed(item)   # _on_cancel set first so cancel() can fire it even now
```

When `FirstOf` cancels the losing pre-triggered event:
- `old_value = item_b`
- `_on_cancel(item_b)` → `queue_b._items.appendleft(item_b)` → item restored.

The same pattern applies to `Container.get()` (restores `_level`) and
`Store.get()` (restores the item to `_items`). Put operations do not set
`_on_cancel` because un-delivering an item to a getter is impossible once
`succeed()` has been called.

This replaces the `_Runner` / `_on_cancel` machinery in asimpy, which
achieved the same result by interrupting a wrapper subprocess and catching
`Interrupt` inside `queue.get()`'s `except` block.

## Requirements Checklist

1. Process class hierarchy: `Process` abstract base class with `init()` +
   `run()`. Users subclass and implement `run()`.

2. Wait for duration / future time: `await self.timeout(delay)` (duration) or
   `await env.timeout(target - env.now)` (future time).

3. Current simulated time: `self.now` (shortcut for `self.env.now`).

4. Interrupt another process: `other_process.interrupt(cause)`. Raises
   `Interrupt(cause)` in the target coroutine.

5. Queues (limited/unlimited, blocking/non-blocking):
   - `Queue(env, capacity=None)` — unlimited or limited.
   - `await queue.get()` — block until item available.
   - `queue.try_get()` — raise `QueueEmpty` if empty.
   - `await queue.put(item)` — block if full.
   - `queue.try_put(item)` — raise `QueueFull` if full.

6. Homogeneous resources (discrete and continuous):
   - `Container(env, capacity, init)` handles both (float amounts = continuous;
     integer amounts = discrete).
   - `await container.get(amount)` / `container.try_get(amount)`.
   - `await container.put(amount)` / `container.try_put(amount)`.
   - `Resource(env, capacity)` for discrete slot-based resources.
   - `await resource.acquire()` / `resource.try_acquire()`.

7. Heterogeneous store:
   - `Store(env, capacity=inf)` with optional filter on get.
   - `await store.get(filter)` / `store.try_get(filter)`.
   - `await store.put(item)` / `store.try_put(item)`.

8. Sleep/wake via store:
   - Process creates `Event(env)`, puts it in a `Store`, awaits it.
   - Claimant gets event from Store, calls `event.succeed(value)`.

9. Barrier: `Barrier(env)`. `await barrier.wait()`. `barrier.release()`.

10. Wait-for-all / wait-for-first:
    - `await AllOf(env, a=evt1, b=evt2)` — returns dict of results.
    - `await FirstOf(env, a=evt1, b=evt2)` — returns `(key, value)` of winner.

11. Simpler than asimpy: elimination of `_ensure_event`, `_Runner`, and
    `_on_cancel` reduces core complexity by roughly a third.
