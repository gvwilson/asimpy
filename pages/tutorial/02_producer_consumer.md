# Producer-Consumer

## Source and Output

```python
--8<-- "examples/02_producer_consumer.py"
```

```text
--8<-- "output/02_producer_consumer.txt"
```

## Key Points

1.  Classes derived from `Process` do initialization in `init()`, *not* `__init__()`,
    and define their behavior in `run()`.

2.  The `Queue` has to be created first so that it can be passed as a constructor argument
    to both `Producer` and `Consumer`.

3.  The producer has to `await` the `put()` operation because it might block
    if the queue has limited capacity and is full.
    This isn't strictly necessary for a queue with infinite capacity,
    but requiring `await` for every `put()` keeps the interface simple.

## Check for Understanding

If the queue's capacity was limited to two objects at a time,
would the behavior of this program change?
