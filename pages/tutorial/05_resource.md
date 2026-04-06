# Resource

## Source and Output

```python
--8<-- "examples/05_resource.py"
```

--8<-- "output/05_resource.txt"

## Key Points

1.  `Resource(env, capacity=N)` creates a pool of `N` slots.  The
    default capacity is 1 (a mutual-exclusion lock).

2.  `acquire()` returns an `Event` that resolves when a slot is
    available.  If all slots are taken the caller blocks until another
    process calls `release()`.

3.  `release()` is synchronous, not `async`.
    It immediately grants the freed slot to the first waiting process, if any.

4.  Workers 2 and 3 arrive while both slots are occupied and wait:
    worker 2 starts at t=3 when worker 0 finishes, and worker 3 starts at t=4
    when worker 1 finishes.

## Check for Understanding

What would happen if a process called `resource.release()` before awaiting its
`timeout(WORK_DURATION)`?
Would another process start its work sooner, later, or at the same time?
