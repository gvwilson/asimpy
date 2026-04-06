# AllOf

## Source and Output

```python
--8<-- "examples/09_all_of.py"
```

--8<-- "output/09_all_of.txt"

## Key Points

1.  `AllOf(env, **events)` is itself an `Event` that triggers only when every
    named child event has triggered.

2.  Its value is a `dict` mapping each keyword to the corresponding child
    event's value.  `Timeout` events resolve to `None`, so all three values
    here are `None`.

3.  The coordinator resumes at t=5 because that is when the last child
    (`gamma`, duration 5) completes.  The faster children (`beta` at t=1,
    `alpha` at t=3) have no visible effect until `gamma` finishes.

## Check for Understanding

If you added a fourth task with duration 0, would the coordinator still see
all four keys in the result `dict`?
At what simulation time would the coordinator resume?
