# Bounded Queue

## Source and Output

```python
--8<-- "examples/03_bounded_queue.py"
```

--8<-- "output/03_bounded_queue.txt"

## Key Points

1.  Consumer happens to run first,
    so it is waiting when the producer creates item 0.
    That item is delivered immediately,
    leaving the queue empty.

1.  The producer can therefore add item 1 to the queue without waiting,
    but when it tries to add item 2,
    the queue is at capacity and the producer blocks.

## Check for Understanding

How would the program's behavior change if the queue's capacity was 2?
