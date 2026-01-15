# Combining Events

So far,
a process can only wait for one event at a time.
In real systems,
though,
processes often need to wait for one of several things to happen.
This tutorial introduces two new coordination primitives:

- `AllOf` waits for all events in a set to complete.
- `FirstOf` waits for the first event to complete and cancels the rest.

## Design Principle

The core idea is that composite events are just events that wait on other events.
An `Event` already knows how to register waiters and resume processes,
so a composite event can:

1.  attach small watcher objects to child events;
2.  decide when it is complete; and
3.  optionally cancel remaining events.

No changes to the scheduler are required.

## `AllOf`

`AllOf` completes when every child event completes.
For example, after:

```python
results = await AllOf(
    env,
    a=self.timeout(5),
    b=self.timeout(10),
)
```

`results` will be `{"a": None, "b": None}` (because `Timeout` returns `None`)
and `env.now` will be 10.
To implement this,
each child event receives a *watcher*:

```python
class _AllOfWatcher:
    def _resume(self, value):
        parent._child_done(key, value)
```

and the parent event simply counts completions:

```
def _child_done(self, key, value):
    self._results[key] = value
    if len(self._results) == len(self._events):
        self.succeed(self._results)
```

Cancellation is not needed because all child events are expected to complete.

## `FirstOf`

`FirstOf` completes when the first child event completes,
i.e.,
exactly one event wins and all other events are cancelled.
We can use this to implement timeouts on events:

```python
name, value = await FirstOf(
    env,
    message=queue.get(),
    timeout=self.timeout(10),
)
if name == "timeout":
    print("no message arrived")
```

However,
we must implement cancellation in order to make this work.
The reason is that many events have side effects,
e.g.,
`queue.get()` removes an item from the queue.
If a losing event was allowed to complete later,
it would corrupt the simulation.

`FirstOf` prevents this by cancelling all non-winning events immediately:

```python
def _child_done(self, key, value, winner):
    for evt in self._events.values():
        if evt is not winner:
            evt.cancel()
    self.succeed((key, value))
```

## Changes Elsewhere

We need to add a generic `cancel` method to `Event`:

```python
class Event:
    def cancel(self):
        if self._triggered or self._cancelled:
            return
        self._cancelled = True
        self._waiters.clear()
        if self._on_cancel:
            self._on_cancel()
```

We also need to add class-specific logic elsewhere.
For example,
when cancelling a `get` from a queue,
we must put the item back at the front of the queue:

```python
class Queue:
    async def get(self):
        if self._items:
            item = self._items.pop(0)
            evt = Event(self._env)
            self._env._immediate(lambda: evt.succeed(item))
            evt._on_cancel = lambda: self._items.insert(0, item)
            return await evt
        else:
            evt = Event(self._env)
            self._getters.append(evt)
            return await evt
```
