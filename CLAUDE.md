# Newsim

The aim of this project is to build a simple, efficient framework for
discrete event simulation in Python using async/await instead of
yield. Its inspirations are:

- Python's simpy library (~/simpy), which is efficient and has a
  relatively simple API, but which uses yield instead of async/await.

- The asimpy library (~/asimpy), which uses async/await, but which is
  less efficient and which has a more complex API.

Examples of use are:

- The lessons in ~/sim, which use asimpy.

- The simulation in ~/calls/sim.py, which uses asimpy, and uses an
  awkward mechanism to simulate the interactions between clients and
  agents.

- The lessons in ~/learn/queueing, which illustrate ideas from
  queueing theory using asimpy.

## Plan

1.  Read the source for simpy from ~/simpy/src/simpy/*.py.

2.  Read the source for asimpy from ~/asimpy/src/asimpy/*.py.

3.  Read the examples from ~/sim/*/*.py.

4.  Read the simulation from ~/calls/sim.py.

5.  Read the marimo notebooks in ~/learn/queueing/*.py.

6.  Write a detailed point-form design for a discrete event simulation
    library that uses async/await instead of yield, but which is much
    simpler in implementation than asimpy. The new library must
    support at least the features given in the "Requirements" section
    below.

## Requirements

1.  Each process in the simulation is an instance of a class derived
    from a class called Process.

2.  A process must be able to wait for a specified duration or until a
    specified future time.

3.  A process must be able to find out what the current simulated time
    is.

4.  One process must be able to interrupt another process by injecting
    an exception into it.

5.  The library must provide queues with both limited and unlimited
    capacity. The library must support processes blocking when they
    attempt to dequeue from an empty queue. The library must also
    support non-blocking "dequeue or fail". The library must support
    two kinds of enqueue: block if queue is full, and fail to enqueue
    if queue is full.

6.  The library must provide discrete and continuous homogeneous
    resources. Attempts to claim content from a resource must be
    provided as both "block until available" and "fail immediately if
    not available".

7.  The library must provide a store of heterogeneous objects that can
    be claimed by processes with the same "block until available" and
    "fail if not available" semantics.

8.  The library must provide a way for a process to sleep until it is
    woken up by another process. This must work in conjunction with
    the store described above, so that a process A can claim and wake
    up a process B from a store.

9.  The library must provide a barrier that multiple processes can
    wait on until some other process releases them.

10. The library must provide "wait for all" and "wait for first" on
    heterogeneous events.

11. The library's internals must be simpler than those of asimpy.
