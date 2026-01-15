# Adding Queues

In the minimal framework, processes could only wait for time.
In real simulations, processes often need to wait for each other.
This step introduces our first coordination primitive,
a first-in/first-out (FIFO) queue that processes can `await` using `get()` and `put()`.

## Design

The queue maintains two internal lists:

```python
self._items    # items currently in the queue
self._getters  # Event objects for waiting consumers
```

If an item is available,
`Queue.get()` removes it and returns it,
resuming the caller at the current simulation time.
If an item is *not* available,
on the other hand,
`Queue.get()` create a new `Event`,
appends it to the `queue._getters` list,
and suspends the calling process by `await`ing the event.

When a process calls `queue.put()` to add something to the queue,
the method checks to see if a consumer is already waiting.
If so,
the consumer is immediately resumed with the item.
Otherwise,
the item is appended to `queue._items`.

Notice that `queue.get()` and `queue.put()` do not advance simulated time.
If putting something in the queue or getting something from it takes time,
the simulation needs to use `Timeout` to model that explicitly.
