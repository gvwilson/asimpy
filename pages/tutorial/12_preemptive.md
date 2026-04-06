# Preemptive Resource

## Source and Output

```python
--8<-- "examples/12_preemptive.py"
```

--8<-- "output/12_preemptive.txt"

## Key Points

1.  `PreemptiveResource` uses priority numbers where a lower number means
    higher priority (0 is best).  When `preempt=True` and the resource is
    full, a new request with better priority ejects the worst current user.

2.  The evicted process receives an `Interrupt` whose cause is a `Preempted`
    dataclass with two fields: `by` (the process that caused the eviction) and
    `usage_since` (the simulation time when the evicted process acquired the
    resource).

3.  Do not call `release()` when handling a `Preempted` interrupt.
    The preemptor has already removed the evicted process from the user list.
    Calling `release()` a second time will raise `RuntimeError`.

4.  The low-priority worker tracks remaining work and re-acquires after the
    high-priority worker finishes.  It resumes at t=5 and completes at t=10
    (5 remaining ticks from where it was interrupted at t=3).

## Check for Understanding

What would change if `HighPriorityWorker` called
`acquire(priority=HIGH_PRIORITY, preempt=False)`?
Would the low-priority worker be interrupted, and when would the
high-priority worker start working?
