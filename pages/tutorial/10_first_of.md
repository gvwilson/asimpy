# FirstOf

## Source and Output

```python
--8<-- "examples/10_first_of.py"
```

--8<-- "output/10_first_of.txt"

## Key Points

1.  `FirstOf(env, **events)` triggers when the first named child event fires.
    Its value is a `(key, value)` tuple identifying the winner.
    All non-winning events are cancelled.

2.  Because `PATIENCE=3 < SERVICE_TIME=5`, the timeout wins and the client
    logs "timed out, leaving" at t=3, before the server delivers at t=5.

3.  Cancelling `queue.get()` puts the slot back so the queue is not silently
    consumed.  The server still puts its result at t=5, but no consumer
    retrieves it so the simulation ends there.

## Check for Understanding

If you set `PATIENCE = 5`, which branch in the client's `if` statement runs?
How does the output change, and why does the server's log entry disappear?
