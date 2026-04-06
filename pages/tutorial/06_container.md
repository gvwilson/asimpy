# Container

## Source and Output

```python
--8<-- "examples/06_container.py"
```

--8<-- "output/06_container.txt"

## Key Points

1.  `Container(env, capacity=N, init=K)` creates a tank that starts at
    level `K` and holds at most `N` units.  Both integers and floats
    are accepted for capacity.

2.  `put(amount)` blocks if adding `amount` would exceed capacity.
    `get(amount)` blocks if the tank holds less than `amount`.

3.  A successful `get()` immediately wakes any pending putter, and a successful
    `put()` immediately wakes any pending getter.  At t=9 the motor's drain
    triggers the pump's blocked add in the same tick, so the log shows the
    pump's entry at t=9 even though no extra time passes.

4.  Unlike `Queue`, a `Container` has no concept of individual items: it
    tracks a single numeric level.

## Check for Understanding

If `init` were 0 instead of 5, the motor would block on its first `get(3)`
at t=3 because the tank would be empty.  At what time would the motor
finally receive those 3 units, and why?
