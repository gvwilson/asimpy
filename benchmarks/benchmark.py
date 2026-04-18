"""Benchmark asimpy features by counting bytecode instructions via sys.monitoring.

Each benchmark function is self-contained: it creates a fresh Environment, runs the
simulation to completion, and does nothing else.  count_instructions() wraps the call
with sys.monitoring to tally every CPython bytecode instruction executed, including
framework and library code inside asimpy itself.  The counts are CPython-version-specific
and should only be compared across runs on the same interpreter.

Several features appear in two variants:

  Unblocked variant (e.g. Queue, AllOf): operations always find a ready counterpart and
  the awaiting process never parks.  This isolates the fast path through the scheduler.

  Blocking variant (e.g. Queue (blocking put), AllOf (blocking)): the process genuinely
  suspends and is later resumed by a sibling process.  This exercises the full
  suspend/resume cycle including heap scheduling.

Non-blocking operations (try_get, try_put, try_acquire) have no await at all; their for
loops run entirely within a single coroutine send() call, so the benchmark captures raw
method-call overhead with no scheduler involvement.
"""

import argparse
import csv
import sys
import polars as pl
from prettytable import PrettyTable, TableStyle

from asimpy import __version__ as asimpy_version
from asimpy import (
    AllOf,
    Barrier,
    Container,
    Environment,
    Event,
    FirstOf,
    Interrupt,
    PreemptiveResource,
    PriorityQueue,
    Process,
    Queue,
    Resource,
    Store,
)

# Number of times each feature is exercised per benchmark run.
NUM = 1000

# sys.monitoring tool slot; 1-5 are reserved for user tools.
TOOL_ID = 1


def count_instructions(func, *args, **kwargs):
    """Return the number of CPython bytecode instructions executed by func."""
    total = [0]

    def _handler(code, offset):
        total[0] += 1

    sys.monitoring.use_tool_id(TOOL_ID, "asimpy-bench")
    sys.monitoring.register_callback(
        TOOL_ID, sys.monitoring.events.INSTRUCTION, _handler
    )
    sys.monitoring.set_events(TOOL_ID, sys.monitoring.events.INSTRUCTION)
    try:
        func(*args, **kwargs)
    finally:
        sys.monitoring.set_events(TOOL_ID, 0)
        sys.monitoring.free_tool_id(TOOL_ID)

    return total[0]


def bench_timeout(num):
    """num Timeout events awaited in a single process."""
    class Proc(Process):
        async def run(self):
            for _ in range(num):
                await self.timeout(1)

    env = Environment()
    Proc(env)
    env.run()


def bench_event(num):
    """num manual Events created, scheduled, and awaited."""
    class Proc(Process):
        async def run(self):
            for _ in range(num):
                evt = Event(self._env)
                self._env.immediate(evt.succeed)
                await evt

    env = Environment()
    Proc(env)
    env.run()


def bench_process(num):
    """num Processes each performing one Timeout."""
    class Worker(Process):
        async def run(self):
            await self.timeout(1)

    env = Environment()
    for _ in range(num):
        Worker(env)
    env.run()


def bench_resource_uncontended(num):
    """num uncontended acquire/release cycles on a Resource."""
    class Proc(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            for _ in range(num):
                await self.res.acquire()
                self.res.release()

    env = Environment()
    Proc(env, Resource(env))
    env.run()


def bench_resource_contention(num):
    """num processes each queuing for and releasing one Resource slot."""
    class Proc(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire()
            await self.timeout(1)
            self.res.release()

    env = Environment()
    res = Resource(env)
    for _ in range(num):
        Proc(env, res)
    env.run()


def bench_preemptive(num):
    """num preemptions of a low-priority process by a high-priority one."""
    interrupted = [0]

    class Victim(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            while interrupted[0] < num:
                try:
                    await self.res.acquire(priority=10)
                    await self.timeout(10)
                    self.res.release()
                except Interrupt:
                    interrupted[0] += 1

    class Interrupter(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            for _ in range(num):
                await self.timeout(1)
                await self.res.acquire(priority=0)
                self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Victim(env, res)
    Interrupter(env, res)
    env.run()


def bench_container(num):
    """num put/get pairs on a Container."""
    class Proc(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            for _ in range(num):
                await self.c.put(1)
                await self.c.get(1)

    env = Environment()
    # capacity=num ensures the container is never full and never empty when accessed,
    # so neither put nor get ever blocks.  This isolates the unblocked fast path.
    Proc(env, Container(env, capacity=num))
    env.run()


def bench_store(num):
    """num put/get pairs on a Store."""
    class Proc(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            for i in range(num):
                await self.s.put(i)
                await self.s.get()

    env = Environment()
    # capacity=num: store never fills, so put never blocks; get follows put each
    # iteration, so the store is never empty when get is called.  Neither operation
    # blocks.  See bench_store_nonblocking for the non-blocking try_put/try_get path.
    Proc(env, Store(env, capacity=num))
    env.run()


def bench_queue(num):
    """num put/get pairs on a Queue."""
    class Proc(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(num):
                await self.q.put(i)
                await self.q.get()

    env = Environment()
    # capacity=num: queue never fills, so put never blocks; get always follows put,
    # so get never blocks either.  See bench_queue_blocking_put/get for the blocked paths.
    Proc(env, Queue(env, capacity=num))
    env.run()


def bench_priority_queue(num):
    """num put/get pairs on a PriorityQueue."""
    class Proc(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(num):
                await self.q.put(i)
                await self.q.get()

    env = Environment()
    # capacity=num: same reasoning as bench_queue; neither put nor get blocks.
    # Items are inserted in ascending order (i increases each iteration), so bisect.insort
    # always appends, giving best-case insertion cost for the sorted structure.
    Proc(env, PriorityQueue(env, capacity=num))
    env.run()


def bench_barrier(num):
    """num barrier wait/release cycles (one waiter, one releaser)."""
    class Waiter(Process):
        def init(self, b):
            self.b = b

        async def run(self):
            for _ in range(num):
                await self.b.wait()

    class Releaser(Process):
        def init(self, b):
            self.b = b

        async def run(self):
            for _ in range(num):
                await self.timeout(1)
                self.b.release()

    env = Environment()
    b = Barrier(env)
    Waiter(env, b)
    Releaser(env, b)
    env.run()


def bench_allof(num):
    """num AllOf completions over two pre-triggered events each."""
    class Proc(Process):
        async def run(self):
            for _ in range(num):
                e1 = Event(self._env)
                e2 = Event(self._env)
                # Both events are triggered before AllOf is constructed, so AllOf
                # resolves immediately and the process never parks.  This isolates
                # the AllOf assembly and completion overhead from scheduling cost.
                e1.succeed()
                e2.succeed()
                await AllOf(self._env, a=e1, b=e2)

    env = Environment()
    Proc(env)
    env.run()


def bench_firstof(num):
    """num FirstOf completions; first of two events pre-triggered."""
    class Proc(Process):
        async def run(self):
            for _ in range(num):
                e1 = Event(self._env)
                e2 = Event(self._env)
                # e1 is triggered before FirstOf is constructed, so FirstOf resolves
                # immediately without parking the process.  e2 is left pending and
                # cancelled by FirstOf, exercising the cancel-losing-event path.
                e1.succeed()
                await FirstOf(self._env, a=e1, b=e2)

    env = Environment()
    Proc(env)
    env.run()


def bench_interrupt(num):
    """num Interrupt deliveries to a process waiting on a Timeout."""
    class Target(Process):
        def init(self):
            self.count = 0

        async def run(self):
            while self.count < num:
                try:
                    await self.timeout(100)
                except Interrupt:
                    self.count += 1

    class Sender(Process):
        def init(self, target):
            self.target = target

        async def run(self):
            for _ in range(num):
                await self.timeout(1)
                self.target.interrupt()

    env = Environment()
    target = Target(env)
    Sender(env, target)
    env.run()


def bench_log(num):
    """num calls to Environment.log."""
    class Proc(Process):
        async def run(self):
            for _ in range(num):
                self._env.log("bench", "message")

    env = Environment()
    Proc(env)
    env.run()


# Slot count for the multi-capacity Resource benchmark.
MULTI_CAPACITY = 4


def bench_queue_blocking_put(num):
    """num put operations that block because the Queue is at capacity."""
    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(num):
                await self.q.put(i)

    class Consumer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for _ in range(num):
                # timeout(1) delays each get so that the Producer's next put always
                # arrives at a full queue (capacity=1) and must block.
                await self.timeout(1)
                await self.q.get()

    env = Environment()
    # capacity=1: Producer's first put fills the queue, and every subsequent put
    # blocks until Consumer drains it.
    q = Queue(env, capacity=1)
    Producer(env, q)
    Consumer(env, q)
    env.run()


def bench_queue_blocking_get(num):
    """num get operations that block because the Queue is empty."""
    class Producer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for i in range(num):
                # timeout(1) delays each put so that Consumer always arrives at an
                # empty queue and must block.
                await self.timeout(1)
                await self.q.put(i)

    class Consumer(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            for _ in range(num):
                await self.q.get()

    env = Environment()
    # No capacity limit: put never blocks; only get blocks (queue starts empty).
    q = Queue(env)
    Producer(env, q)
    Consumer(env, q)
    env.run()


def bench_queue_nonblocking(num):
    """num try_put/try_get pairs on a Queue (non-blocking happy path)."""
    class Proc(Process):
        def init(self, q):
            self.q = q

        async def run(self):
            # No await: the entire for loop runs inside a single coroutine send().
            # This measures raw try_put/try_get method overhead with no scheduler
            # involvement.
            for i in range(num):
                self.q.try_put(i)
                self.q.try_get()

    env = Environment()
    Proc(env, Queue(env))
    env.run()


def bench_store_nonblocking(num):
    """num try_put/try_get pairs on a Store (non-blocking happy path)."""
    class Proc(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            # No await: entire loop runs in one send(), same reasoning as
            # bench_queue_nonblocking.
            for i in range(num):
                self.s.try_put(i)
                self.s.try_get()

    env = Environment()
    Proc(env, Store(env))
    env.run()


def bench_store_filtered_get(num):
    """num Store.get(filter=...) calls where the filter matches every item."""
    # Defined once outside the loop to avoid creating a new lambda object each iteration.
    accept_all = lambda x: True  # noqa: E731

    class Proc(Process):
        def init(self, s):
            self.s = s

        async def run(self):
            for i in range(num):
                await self.s.put(i)
                await self.s.get(filter=accept_all)

    env = Environment()
    Proc(env, Store(env))
    env.run()


def bench_container_nonblocking(num):
    """num try_put/try_get pairs on a Container (non-blocking happy path)."""
    class Proc(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            # No await: entire loop runs in one send().  capacity=1 is sufficient
            # because try_put(1) and try_get(1) alternate, keeping the level at 0
            # or 1 and never exceeding capacity.
            for _ in range(num):
                self.c.try_put(1)
                self.c.try_get(1)

    env = Environment()
    Proc(env, Container(env, capacity=1))
    env.run()


def bench_container_float(num):
    """num put/get pairs on a Container using float amounts."""
    class Proc(Process):
        def init(self, c):
            self.c = c

        async def run(self):
            for _ in range(num):
                await self.c.put(0.5)
                await self.c.get(0.5)

    env = Environment()
    # capacity=1.0: each put(0.5)/get(0.5) pair keeps the level between 0.0 and 0.5,
    # so neither operation blocks.  Using floats exercises the float arithmetic path
    # in Container._trigger_getters/_trigger_putters rather than integer comparison.
    Proc(env, Container(env, capacity=1.0))
    env.run()


def bench_resource_try_acquire(num):
    """num try_acquire/release cycles on a Resource (non-blocking acquire)."""
    class Proc(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            # No await: entire loop runs in one send().  try_acquire() returns True
            # each time because release() frees the slot before the next iteration.
            for _ in range(num):
                self.res.try_acquire()
                self.res.release()

    env = Environment()
    Proc(env, Resource(env))
    env.run()


def bench_resource_multi_capacity(num):
    """num processes sharing a Resource with capacity MULTI_CAPACITY."""
    class Proc(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            await self.res.acquire()
            await self.timeout(1)
            self.res.release()

    env = Environment()
    # MULTI_CAPACITY slots run concurrently; the remaining num-MULTI_CAPACITY processes
    # queue and are woken in batches as each group of holders releases.  This exercises
    # the multi-waiter wakeup path, unlike bench_resource_contention (1 slot, strict
    # FIFO) and bench_resource_uncontended (1 slot, no competition).
    res = Resource(env, capacity=MULTI_CAPACITY)
    for _ in range(num):
        Proc(env, res)
    env.run()


def bench_resource_context_manager(num):
    """num acquire/release cycles via the Resource async context manager."""
    class Proc(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            for _ in range(num):
                async with self.res:
                    pass

    env = Environment()
    Proc(env, Resource(env))
    env.run()


def bench_preemptive_no_preempt(num):
    """num blocking acquires with preempt=False; high-priority waiter queues instead of preempting."""
    class Holder(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            # priority=10 is lower priority (higher number = worse).
            for _ in range(num):
                await self.res.acquire(priority=10)
                await self.timeout(1)
                self.res.release()

    class Waiter(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            # priority=0 is higher priority, but preempt=False suppresses eviction
            # of Holder.  Waiter joins the waiters queue and blocks until Holder
            # releases, exercising the non-preempting blocking-acquire path.
            for _ in range(num):
                await self.res.acquire(priority=0, preempt=False)
                self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Holder(env, res)
    Waiter(env, res)
    env.run()


def bench_preempted_cause(num):
    """num preemptions where the victim reads Preempted.by and .usage_since."""
    interrupted = [0]

    class Victim(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            while interrupted[0] < num:
                try:
                    await self.res.acquire(priority=10)
                    await self.timeout(10)
                    self.res.release()
                except Interrupt as exc:
                    interrupted[0] += 1
                    # Read both fields of the Preempted dataclass; compare with
                    # bench_preemptive which catches Interrupt but ignores the cause.
                    _ = exc.cause.by
                    _ = exc.cause.usage_since

    class Interrupter(Process):
        def init(self, res):
            self.res = res

        async def run(self):
            for _ in range(num):
                await self.timeout(1)
                await self.res.acquire(priority=0)
                self.res.release()

    env = Environment()
    res = PreemptiveResource(env)
    Victim(env, res)
    Interrupter(env, res)
    env.run()


def bench_event_fail(num):
    """num Events triggered via fail() whose exception is caught by the awaiter."""
    class Proc(Process):
        async def run(self):
            for _ in range(num):
                evt = Event(self._env)
                self._env.immediate(lambda e=evt: e.fail(ValueError("x")))
                try:
                    await evt
                except ValueError:
                    pass

    env = Environment()
    Proc(env)
    env.run()


def bench_event_cancel(num):
    """num Event.cancel() calls on pending events."""
    class Proc(Process):
        async def run(self):
            # No await: the for loop runs entirely in one send() call, because
            # cancelling a pending event never yields control.  The coroutine
            # completes in a single step and Process._loop catches StopIteration.
            for _ in range(num):
                evt = Event(self._env)
                evt.cancel()

    env = Environment()
    Proc(env)
    env.run()


def bench_interrupt_with_cause(num):
    """num Interrupt deliveries where the sender sets a cause and the receiver reads it."""
    class Target(Process):
        def init(self):
            self.count = 0

        async def run(self):
            while self.count < num:
                try:
                    await self.timeout(100)
                except Interrupt as exc:
                    self.count += 1
                    _ = exc.cause

    class Sender(Process):
        def init(self, target):
            self.target = target

        async def run(self):
            for _ in range(num):
                await self.timeout(1)
                self.target.interrupt(cause="signal")

    env = Environment()
    target = Target(env)
    Sender(env, target)
    env.run()


def bench_run_until(num):
    """Simulation with an infinite process stopped by env.run(until=num)."""
    class Proc(Process):
        async def run(self):
            while True:
                await self.timeout(1)

    env = Environment()
    Proc(env)
    # The process fires exactly num timeouts before until=num stops the simulation.
    # This exercises the until= early-exit check in Environment.run() on every
    # heap pop, in contrast to all other benchmarks that run until the heap is empty.
    env.run(until=num)


def bench_get_log(num):
    """num calls to Environment.get_log."""
    class Proc(Process):
        async def run(self):
            # No await: same single-send() reasoning as other non-blocking loops.
            # Called on an empty log each time, measuring retrieval overhead alone;
            # contrast with bench_log which measures the cost of appending entries.
            for _ in range(num):
                self._env.get_log()

    env = Environment()
    Proc(env)
    env.run()


def bench_allof_async(num):
    """num AllOf completions where child events are triggered by a sibling process."""
    # Shared list lets Waiter hand event pairs to Releaser without extra primitives.
    pending = []

    class Waiter(Process):
        async def run(self):
            for _ in range(num):
                e1, e2 = Event(self._env), Event(self._env)
                pending.append((e1, e2))
                # Parks here: neither e1 nor e2 is triggered yet.
                await AllOf(self._env, a=e1, b=e2)

    class Releaser(Process):
        async def run(self):
            for _ in range(num):
                # timeout(1) gives Waiter time to park on AllOf before Releaser
                # triggers the events, ensuring the blocking suspend/resume path.
                await self.timeout(1)
                e1, e2 = pending.pop(0)
                e1.succeed()
                e2.succeed()

    env = Environment()
    Waiter(env)
    Releaser(env)
    env.run()


def bench_firstof_async(num):
    """num FirstOf completions; one of two pending events triggered, the other cancelled."""
    # Shared list: same coordination pattern as bench_allof_async.
    pending = []

    class Waiter(Process):
        async def run(self):
            for _ in range(num):
                e1, e2 = Event(self._env), Event(self._env)
                pending.append((e1, e2))
                # Parks here: neither event is triggered yet.
                await FirstOf(self._env, a=e1, b=e2)

    class Releaser(Process):
        async def run(self):
            for _ in range(num):
                # timeout(1) ensures Waiter has parked on FirstOf before events fire.
                await self.timeout(1)
                e1, e2 = pending.pop(0)
                # Only e1 is triggered; FirstOf cancels the losing e2, exercising
                # the cancel-non-winning-event path in addition to the wakeup path.
                e1.succeed()

    env = Environment()
    Waiter(env)
    Releaser(env)
    env.run()


BENCHMARKS = [
    ("AllOf",                               bench_allof),
    ("AllOf (blocking)",                    bench_allof_async),
    ("Barrier",                             bench_barrier),
    ("Container",                           bench_container),
    ("Container (float amounts)",           bench_container_float),
    ("Container (non-blocking)",            bench_container_nonblocking),
    ("Environment.get_log",                 bench_get_log),
    ("Environment.log",                     bench_log),
    ("Environment.run(until=)",             bench_run_until),
    ("Event",                               bench_event),
    ("Event (cancel)",                      bench_event_cancel),
    ("Event (fail)",                        bench_event_fail),
    ("FirstOf",                             bench_firstof),
    ("FirstOf (blocking)",                  bench_firstof_async),
    ("Interrupt",                           bench_interrupt),
    ("Interrupt (with cause)",              bench_interrupt_with_cause),
    ("PreemptiveResource",                  bench_preemptive),
    ("PreemptiveResource (cause fields)",   bench_preempted_cause),
    ("PreemptiveResource (no-preempt)",     bench_preemptive_no_preempt),
    ("PriorityQueue",                       bench_priority_queue),
    ("Process",                             bench_process),
    ("Queue",                               bench_queue),
    ("Queue (blocking get)",                bench_queue_blocking_get),
    ("Queue (blocking put)",                bench_queue_blocking_put),
    ("Queue (non-blocking)",                bench_queue_nonblocking),
    ("Resource (contention)",               bench_resource_contention),
    ("Resource (context manager)",          bench_resource_context_manager),
    ("Resource (multi-capacity)",           bench_resource_multi_capacity),
    ("Resource (try_acquire)",              bench_resource_try_acquire),
    ("Resource (uncontended)",              bench_resource_uncontended),
    ("Store",                               bench_store),
    ("Store (filtered get)",                bench_store_filtered_get),
    ("Store (non-blocking)",                bench_store_nonblocking),
    ("Timeout",                             bench_timeout),
]


def benchmark():
    """Run all benchmarks and return results as a Polars DataFrame."""
    features, executions, instructions, instr_per_exec = [], [], [], []
    for name, func in BENCHMARKS:
        count = count_instructions(func, NUM)
        features.append(name)
        executions.append(NUM)
        instructions.append(count)
        instr_per_exec.append(count / NUM)
    return pl.DataFrame({
        "Feature": features,
        "Executions": executions,
        "Instructions": instructions,
        "Instr/Execution": instr_per_exec,
    })


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark asimpy features.")
    parser.add_argument(
        "--format",
        metavar="NAME",
        choices=["csv", "markdown"],
        default="markdown",
        help="output format: csv or markdown (default: markdown)",
    )
    parser.add_argument(
        "--output",
        metavar="FILENAME",
        help="write results to this file (default: stdout)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="show version header in output",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    df = benchmark()

    newline = "" if args.format == "csv" else None
    out = open(args.output, "w", newline=newline) if args.output else sys.stdout
    try:
        if args.version:
            print(f"# asimpy version {asimpy_version}\n", file=out)
        if args.format == "csv":
            writer = csv.writer(out)
            writer.writerow(["Feature", "Executions", "Instructions", "Instr/Execution"])
            for row in df.iter_rows():
                feature, execs, instr, rate = row
                writer.writerow([feature, execs, instr, f"{rate:.1f}"])
        else:
            table = PrettyTable()
            table.set_style(TableStyle.MARKDOWN)
            table.field_names = ["Feature", "Executions", "Instructions", "Instr/Execution"]
            table.align["Feature"] = "l"
            table.align["Executions"] = "r"
            table.align["Instructions"] = "r"
            table.align["Instr/Execution"] = "r"
            for row in df.iter_rows():
                feature, execs, instr, rate = row
                table.add_row([feature, execs, instr, f"{rate:.1f}"])
            print(table, file=out)
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
