# Store

## Source and Output

```python
--8<-- "examples/08_store.py"
```

--8<-- "output/08_store.txt"

## Key Points

1.  `Store` holds heterogeneous items and supports selective retrieval.
    `get(filter=fn)` returns the first item for which `fn(item)` is `True`.
    If `filter` is `None`, any item is accepted.

2.  If no matching item is available the caller blocks until a subsequent
    `put()` delivers one.  Both pickers are already waiting when the stacker
    puts the first item at t=1.

3.  Items are matched in insertion order: the first red item is returned to
    the first red-picker waiting, and so on.

4.  Unlike `Queue`, items do not need to be comparable.
    The store is a plain list searched linearly by the filter function.

## Check for Understanding

What would `get()` return if called without a filter while the store contained
both `"red"` and `"blue"` items?
