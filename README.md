# asimpy

A simple discrete event simulation framework in Python using `async`/`await`.

-   [Documentation][asimpy]
-   [Package][package]
-   [Repository][repo]

*Thanks to the creators of [SimPy][simpy] for inspiration.*

## Core Concepts

Discrete event simulation (DES) simulates systems in which events occur at discrete points in time.
The simulation maintains a virtual clock and executes events in chronological order.
Unlike real-time systems,
the simulation jumps directly from one event time to the next,
skipping empty intervals.
(Time steps are often referred to as "ticks".)

## Async/Await

Python's `async`/`await` syntax enables cooperative multitasking without threads.
Functions defined as `async def` return coroutine objects when called.
These coroutines can be paused at `await` points and later resumed.
More specifically,
when a coroutine executes `value = await expr`, it:

1.  yields the awaited object `expr` to its caller;
2.  suspends execution at that point;
3.  resumes later when `send(value)` is called on it; an thend
4.  returns the value passed to `send()` as the result of the `await` expression
    inside the resumed coroutine.

[asimpy][asimpy] uses this mechanism to pause and resume coroutines to simulate simultaneously execution.
This is similar to the `yield`-based mechanism used in [SimPy][simpy].

[asimpy]: https://asimpy.readthedocs.io/
[package]: https://pypi.org/project/asimpy/
[repo]: https://github.com/gvwilson/asimpy
[simpy]: https://simpy.readthedocs.io/
