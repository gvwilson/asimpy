"""Benchmark asimpy features against plain Python operations."""

import argparse
import csv
import sys
import time

from asimpy import (
    AllOf,
    Barrier,
    BlockingQueue,
    Environment,
    Event,
    FirstOf,
    Interrupt,
    Process,
    Queue,
    Resource,
    Timeout,
)


def run(label, func, n):
    """Run func(n), print elapsed time, and return the time."""
    start = time.perf_counter()
    func(n)
    elapsed = time.perf_counter() - start
    return [label, elapsed, None]


def bench_sum(n):
    """Sum integers 0..n-1."""
    total = 0
    for i in range(n):
        total += i


def bench_list(n):
    """Append and pop from a list n times."""
    items = []
    for i in range(n):
        items.append(i)
    for i in range(n):
        items.pop(0)


def bench_timeout(n):
    """Create n processes that each do a single timeout."""

    class Sleeper(Process):
        async def run(self):
            await self.timeout(1)

    env = Environment()
    for _ in range(n):
        Sleeper(env)
    env.run()


def bench_event_succeed(n):
    """Create and succeed n events."""
    env = Environment()
    for _ in range(n):
        evt = Event(env)
        evt.succeed(42)


def bench_queue_put_get(n):
    """Put then get n items through a Queue."""

    class Producer(Process):
        def init(self, q, count):
            self.q = q
            self.count = count

        async def run(self):
            for i in range(self.count):
                self.q.put(i)

    class Consumer(Process):
        def init(self, q, count):
            self.q = q
            self.count = count

        async def run(self):
            await self.timeout(1)
            for _ in range(self.count):
                await self.q.get()

    env = Environment()
    q = Queue(env)
    Producer(env, q, n)
    Consumer(env, q, n)
    env.run()


def bench_queue_blocking_get(n):
    """Producer-consumer with consumer waiting on each item."""

    class Producer(Process):
        def init(self, q, count):
            self.q = q
            self.count = count

        async def run(self):
            for i in range(self.count):
                await self.timeout(1)
                self.q.put(i)

    class Consumer(Process):
        def init(self, q, count):
            self.q = q
            self.count = count

        async def run(self):
            for _ in range(self.count):
                await self.q.get()

    env = Environment()
    q = Queue(env)
    Producer(env, q, n)
    Consumer(env, q, n)
    env.run()


def bench_priority_queue(n):
    """Put n items into a priority queue then get them in order."""

    class PQUser(Process):
        def init(self, pq, count):
            self.pq = pq
            self.count = count

        async def run(self):
            for i in range(self.count, 0, -1):
                self.pq.put(i)
            await self.timeout(1)
            for _ in range(self.count):
                await self.pq.get()

    env = Environment()
    pq = Queue(env, priority=True)
    PQUser(env, pq, n)
    env.run()


def bench_blocking_queue(n):
    """Producer-consumer through a BlockingQueue with capacity 10."""

    class Producer(Process):
        def init(self, bq, count):
            self.bq = bq
            self.count = count

        async def run(self):
            for i in range(self.count):
                await self.bq.put(i)

    class Consumer(Process):
        def init(self, bq, count):
            self.bq = bq
            self.count = count

        async def run(self):
            for _ in range(self.count):
                await self.bq.get()

    env = Environment()
    bq = BlockingQueue(env, max_capacity=10)
    Producer(env, bq, n)
    Consumer(env, bq, n)
    env.run()


def bench_resource(n):
    """n processes each acquire and release a shared resource."""

    class Worker(Process):
        async def run(self):
            await self.resource.acquire()
            await self.timeout(1)
            await self.resource.release()

    env = Environment()
    res = Resource(env, capacity=5)
    for _ in range(n):
        w = Worker(env)
        w.resource = res
    env.run()


def bench_barrier(n):
    """n processes wait at a barrier, then one process releases them."""

    class Waiter(Process):
        def init(self, bar):
            self.bar = bar

        async def run(self):
            await self.bar.wait()

    class Releaser(Process):
        def init(self, bar):
            self.bar = bar

        async def run(self):
            await self.timeout(1)
            await self.bar.release()

    env = Environment()
    bar = Barrier(env)
    for _ in range(n):
        Waiter(env, bar)
    Releaser(env, bar)
    env.run()


def bench_allof(n):
    """Wait for n timeouts using AllOf."""

    class Joiner(Process):
        def init(self, count):
            self.count = count

        async def run(self):
            events = {f"t{i}": self.timeout(i + 1) for i in range(self.count)}
            await AllOf(self._env, **events)

    env = Environment()
    Joiner(env, n)
    env.run()


def bench_firstof(n):
    """Race n timeouts using FirstOf, repeated n times."""

    class Racer(Process):
        def init(self, rounds):
            self.rounds = rounds

        async def run(self):
            for _ in range(self.rounds):
                await FirstOf(
                    self._env,
                    fast=self.timeout(1),
                    slow=self.timeout(10),
                )

    env = Environment()
    Racer(env, n)
    env.run()


def bench_interrupt(n):
    """n processes get interrupted."""

    class Sleeper(Process):
        def init(self, interruptible):
            self.interruptible = interruptible

        async def run(self):
            try:
                await self.timeout(1000)
            except Interrupt:
                pass

    class Interrupter(Process):
        def init(self, targets):
            self.targets = targets

        async def run(self):
            await self.timeout(1)
            for t in self.targets:
                t.interrupt("wake up")

    env = Environment()
    targets = [Sleeper(env, True) for _ in range(n)]
    Interrupter(env, targets)
    env.run()


def bench_mixed_simulation(n):
    """A mixed simulation with producers, consumers, and resources."""

    class Producer(Process):
        def init(self, q, count):
            self.q = q
            self.count = count

        async def run(self):
            for i in range(self.count):
                await self.timeout(1)
                self.q.put(i)

    class Consumer(Process):
        def init(self, q, res, count):
            self.q = q
            self.res = res
            self.count = count

        async def run(self):
            for _ in range(self.count):
                item = await self.q.get()
                await self.res.acquire()
                await self.timeout(2)
                await self.res.release()

    env = Environment()
    q = Queue(env)
    res = Resource(env, capacity=3)
    num_producers = 4
    num_consumers = 4
    items_per = n // num_producers

    for _ in range(num_producers):
        Producer(env, q, items_per)
    for _ in range(num_consumers):
        Consumer(env, q, res, items_per)
    env.run()


def main():
    parser = argparse.ArgumentParser(description="Benchmark asimpy")
    parser.add_argument("n", type=int, help="number of iterations for each benchmark")
    args = parser.parse_args()
    n = args.n

    results = []
    for name, obj in globals().items():
        if name.startswith("bench_"):
            results.append(run(name.replace("bench_", ""), obj, n))

    smallest = min(r[1] for r in results)
    for row in results:
        row[2] = round(row[1] / smallest, 1)

    results.insert(0, ["benchmark", "time", "ratio"])
    csv.writer(sys.stdout).writerows(results)


if __name__ == "__main__":
    main()
