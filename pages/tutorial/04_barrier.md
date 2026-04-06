# Barrier

## Source and Output

```python
--8<-- "examples/04_barrier.py"
```

--8<-- "output/04_barrier.txt"

## Key Points

1.  `Waiter` processes all arrive at the barrier before the `Releaser` releases it.

1.  `Barrier.release()` is *not* an `async` operation,
    so `Waiter` doesn't release it.

## Check for Understanding

What would happen to a `Waiter` that called `barrier.wait()` *after* it was released?
