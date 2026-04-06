# Priority Queue

## Source and Output

```python
--8<-- "examples/07_priority_queue.py"
```

--8<-- "output/07_priority_queue.txt"

## Key Points

1.  `PriorityQueue` is a drop-in replacement for `Queue` that serves items in
    ascending sorted order rather than arrival order.  Items must be comparable.

2.  Tuples compare lexicographically in Python, so `(priority, label)` pairs
    are ordered first by priority number and then by label string.
    Wrapping jobs in a tuple is a simple way to attach a priority.

3.  All four jobs are submitted at t=0.  The server picks the smallest tuple
    each time: `(1, "high-B")` before `(1, "high-D")` (same priority, earlier
    alphabetically) before `(2, "mid-C")` before `(3, "low-A")`.

4.  Arrival order has no effect once items are in the queue: `(3, "low-A")` was
    submitted first but served last.

## Check for Understanding

If you changed the label `"high-B"` to `"high-Z"`, would `(1, "high-D")` or
`(1, "high-Z")` be served first, and why?
