"""Benchmark simpy features by counting bytecode instructions via sys.monitoring.

SimPy uses generator-based coroutines (yield) instead of async/await.
Each benchmark creates a fresh Environment, runs to completion, and does nothing else.

Benchmarks omitted because SimPy has no equivalent:
  - Non-blocking operations (try_put, try_get, try_acquire)
  - Event.cancel()
  - Environment.log / get_log

Adaptations:
  - Barrier: implemented with a shared Event (SimPy has no Barrier primitive).
  - Queue / PriorityQueue: mapped to Store / PriorityStore.
  - FirstOf: mapped to AnyOf (env.any_of).
"""

import argparse
import csv
import sys
import polars as pl
from prettytable import PrettyTable, TableStyle

import simpy
from simpy.resources.store import FilterStore, PriorityStore

try:
    simpy_version = simpy.__version__
except AttributeError:
    simpy_version = "unknown"

# Number of times each feature is exercised per benchmark run.
NUM = 1000

# sys.monitoring tool slot; 1-5 are reserved for user tools.
TOOL_ID = 1


def count_instructions(func, *args, **kwargs):
    """Return the number of CPython bytecode instructions executed by func."""
    total = [0]

    def _handler(code, offset):
        total[0] += 1

    sys.monitoring.use_tool_id(TOOL_ID, "simpy-bench")
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
    """num Timeout events yielded in a single process."""
    def proc(env):
        for _ in range(num):
            yield env.timeout(1)

    env = simpy.Environment()
    env.process(proc(env))
    env.run()


def bench_event(num):
    """num manual Events created, scheduled, and yielded."""
    def proc(env):
        for _ in range(num):
            evt = env.event()
            evt.succeed()
            yield evt

    env = simpy.Environment()
    env.process(proc(env))
    env.run()


def bench_process(num):
    """num Processes each performing one Timeout."""
    def worker(env):
        yield env.timeout(1)

    env = simpy.Environment()
    for _ in range(num):
        env.process(worker(env))
    env.run()


def bench_resource_uncontended(num):
    """num uncontended request/release cycles on a Resource."""
    def proc(env, res):
        for _ in range(num):
            req = res.request()
            yield req
            res.release(req)

    env = simpy.Environment()
    env.process(proc(env, simpy.Resource(env)))
    env.run()


def bench_resource_contention(num):
    """num processes each queuing for and releasing one Resource slot."""
    def proc(env, res):
        req = res.request()
        yield req
        yield env.timeout(1)
        res.release(req)

    env = simpy.Environment()
    res = simpy.Resource(env)
    for _ in range(num):
        env.process(proc(env, res))
    env.run()


def bench_preemptive(num):
    """num preemptions of a low-priority process by a high-priority one."""
    interrupted = [0]

    def victim(env, res):
        while interrupted[0] < num:
            req = res.request(priority=10)
            yield req
            try:
                yield env.timeout(10)
                res.release(req)
            except simpy.Interrupt:
                # Preemption removes the request from users; do not release.
                interrupted[0] += 1

    def interrupter(env, res):
        for _ in range(num):
            yield env.timeout(1)
            req = res.request(priority=0)
            yield req
            res.release(req)

    env = simpy.Environment()
    res = simpy.PreemptiveResource(env)
    env.process(victim(env, res))
    env.process(interrupter(env, res))
    env.run()


def bench_container(num):
    """num put/get pairs on a Container."""
    def proc(env, c):
        for _ in range(num):
            yield c.put(1)
            yield c.get(1)

    env = simpy.Environment()
    # capacity=num ensures neither put nor get ever blocks.
    env.process(proc(env, simpy.Container(env, capacity=num)))
    env.run()


def bench_store(num):
    """num put/get pairs on a Store."""
    def proc(env, s):
        for i in range(num):
            yield s.put(i)
            yield s.get()

    env = simpy.Environment()
    # capacity=num: put never blocks; get follows put so never blocks either.
    env.process(proc(env, simpy.Store(env, capacity=num)))
    env.run()


def bench_queue(num):
    """num put/get pairs on a Store used as a FIFO queue."""
    def proc(env, s):
        for i in range(num):
            yield s.put(i)
            yield s.get()

    env = simpy.Environment()
    # capacity=num: same reasoning as bench_store; neither operation blocks.
    env.process(proc(env, simpy.Store(env, capacity=num)))
    env.run()


def bench_priority_queue(num):
    """num put/get pairs on a PriorityStore."""
    def proc(env, s):
        for i in range(num):
            yield s.put(i)
            yield s.get()

    env = simpy.Environment()
    # capacity=num: neither put nor get blocks. Items are integers (orderable).
    env.process(proc(env, PriorityStore(env, capacity=num)))
    env.run()


def bench_barrier(num):
    """num barrier wait/release cycles using a shared Event."""
    # SimPy has no Barrier primitive; a shared Event provides the same
    # suspend/resume pattern: waiter parks on the event, releaser triggers it.
    events = [None]

    def waiter(env):
        for _ in range(num):
            events[0] = env.event()
            yield events[0]

    def releaser(env):
        for _ in range(num):
            # timeout(1) ensures waiter has parked before releaser fires.
            yield env.timeout(1)
            events[0].succeed()

    env = simpy.Environment()
    env.process(waiter(env))
    env.process(releaser(env))
    env.run()


def bench_allof(num):
    """num AllOf completions over two pre-triggered events each."""
    def proc(env):
        for _ in range(num):
            e1 = env.event()
            e2 = env.event()
            # Both events triggered before all_of is constructed, so it
            # resolves immediately without parking the process.
            e1.succeed()
            e2.succeed()
            yield env.all_of([e1, e2])

    env = simpy.Environment()
    env.process(proc(env))
    env.run()


def bench_anyof(num):
    """num AnyOf completions; first of two events pre-triggered."""
    def proc(env):
        for _ in range(num):
            e1 = env.event()
            e2 = env.event()
            # e1 triggered before any_of, so any_of resolves immediately.
            e1.succeed()
            yield env.any_of([e1, e2])

    env = simpy.Environment()
    env.process(proc(env))
    env.run()


def bench_interrupt(num):
    """num Interrupt deliveries to a process waiting on a Timeout."""
    count = [0]

    def target(env):
        while count[0] < num:
            try:
                yield env.timeout(100)
            except simpy.Interrupt:
                count[0] += 1

    def sender(env, target_proc):
        for _ in range(num):
            yield env.timeout(1)
            target_proc.interrupt()

    env = simpy.Environment()
    target_proc = env.process(target(env))
    env.process(sender(env, target_proc))
    env.run()


def bench_event_fail(num):
    """num Events triggered via fail() whose exception is caught by the yielder."""
    def proc(env):
        for _ in range(num):
            evt = env.event()
            evt.fail(ValueError("x"))
            try:
                yield evt
            except ValueError:
                pass

    env = simpy.Environment()
    env.process(proc(env))
    env.run()


def bench_run_until(num):
    """Simulation with an infinite process stopped by env.run(until=num)."""
    def proc(env):
        while True:
            yield env.timeout(1)

    env = simpy.Environment()
    env.process(proc(env))
    env.run(until=num)


# Slot count for the multi-capacity Resource benchmark.
MULTI_CAPACITY = 4


def bench_queue_blocking_put(num):
    """num put operations that block because the Store is at capacity."""
    def producer(env, s):
        for i in range(num):
            yield s.put(i)

    def consumer(env, s):
        for _ in range(num):
            # timeout(1) delays each get so producer's next put always
            # finds the store full (capacity=1) and must block.
            yield env.timeout(1)
            yield s.get()

    env = simpy.Environment()
    # capacity=1: producer's first put fills the store; every subsequent
    # put blocks until consumer drains it.
    s = simpy.Store(env, capacity=1)
    env.process(producer(env, s))
    env.process(consumer(env, s))
    env.run()


def bench_queue_blocking_get(num):
    """num get operations that block because the Store is empty."""
    def producer(env, s):
        for i in range(num):
            # timeout(1) delays each put so consumer always finds the
            # store empty and must block.
            yield env.timeout(1)
            yield s.put(i)

    def consumer(env, s):
        for _ in range(num):
            yield s.get()

    env = simpy.Environment()
    # No capacity limit: put never blocks; only get blocks (store starts empty).
    s = simpy.Store(env)
    env.process(producer(env, s))
    env.process(consumer(env, s))
    env.run()


def bench_store_filtered_get(num):
    """num FilterStore.get(filter=...) calls where the filter matches every item."""
    # Defined once outside the loop to avoid creating a new lambda each iteration.
    accept_all = lambda x: True  # noqa: E731

    def proc(env, s):
        for i in range(num):
            yield s.put(i)
            yield s.get(accept_all)

    env = simpy.Environment()
    env.process(proc(env, FilterStore(env)))
    env.run()


def bench_container_float(num):
    """num put/get pairs on a Container using float amounts."""
    def proc(env, c):
        for _ in range(num):
            yield c.put(0.5)
            yield c.get(0.5)

    env = simpy.Environment()
    # capacity=1.0: each put(0.5)/get(0.5) pair keeps the level between
    # 0.0 and 0.5, so neither operation blocks.
    env.process(proc(env, simpy.Container(env, capacity=1.0)))
    env.run()


def bench_resource_multi_capacity(num):
    """num processes sharing a Resource with capacity MULTI_CAPACITY."""
    def proc(env, res):
        req = res.request()
        yield req
        yield env.timeout(1)
        res.release(req)

    env = simpy.Environment()
    # MULTI_CAPACITY slots run concurrently; remaining processes queue and
    # are woken in batches as holders release.
    res = simpy.Resource(env, capacity=MULTI_CAPACITY)
    for _ in range(num):
        env.process(proc(env, res))
    env.run()


def bench_resource_context_manager(num):
    """num request/release cycles via the Resource context manager."""
    def proc(env, res):
        for _ in range(num):
            with res.request() as req:
                yield req

    env = simpy.Environment()
    env.process(proc(env, simpy.Resource(env)))
    env.run()


def bench_preemptive_no_preempt(num):
    """num blocking requests with preempt=False; high-priority waiter queues instead of preempting."""
    def holder(env, res):
        for _ in range(num):
            req = res.request(priority=10)
            yield req
            yield env.timeout(1)
            res.release(req)

    def waiter(env, res):
        for _ in range(num):
            # priority=0 is higher priority, but preempt=False suppresses
            # eviction of holder. Waiter queues and blocks until holder releases.
            req = res.request(priority=0, preempt=False)
            yield req
            res.release(req)

    env = simpy.Environment()
    res = simpy.PreemptiveResource(env)
    env.process(holder(env, res))
    env.process(waiter(env, res))
    env.run()


def bench_preempted_cause(num):
    """num preemptions where the victim reads Preempted.by and .usage_since."""
    interrupted = [0]

    def victim(env, res):
        while interrupted[0] < num:
            req = res.request(priority=10)
            yield req
            try:
                yield env.timeout(10)
                res.release(req)
            except simpy.Interrupt as exc:
                interrupted[0] += 1
                _ = exc.cause.by
                _ = exc.cause.usage_since

    def interrupter(env, res):
        for _ in range(num):
            yield env.timeout(1)
            req = res.request(priority=0)
            yield req
            res.release(req)

    env = simpy.Environment()
    res = simpy.PreemptiveResource(env)
    env.process(victim(env, res))
    env.process(interrupter(env, res))
    env.run()


def bench_interrupt_with_cause(num):
    """num Interrupt deliveries where the sender sets a cause and the receiver reads it."""
    count = [0]

    def target(env):
        while count[0] < num:
            try:
                yield env.timeout(100)
            except simpy.Interrupt as exc:
                count[0] += 1
                _ = exc.cause

    def sender(env, target_proc):
        for _ in range(num):
            yield env.timeout(1)
            target_proc.interrupt(cause="signal")

    env = simpy.Environment()
    target_proc = env.process(target(env))
    env.process(sender(env, target_proc))
    env.run()


def bench_allof_async(num):
    """num AllOf completions where child events are triggered by a sibling process."""
    pending = []

    def waiter(env):
        for _ in range(num):
            e1, e2 = env.event(), env.event()
            pending.append((e1, e2))
            # Parks here: neither event is triggered yet.
            yield env.all_of([e1, e2])

    def releaser(env):
        for _ in range(num):
            # timeout(1) gives waiter time to park before events fire.
            yield env.timeout(1)
            e1, e2 = pending.pop(0)
            e1.succeed()
            e2.succeed()

    env = simpy.Environment()
    env.process(waiter(env))
    env.process(releaser(env))
    env.run()


def bench_anyof_async(num):
    """num AnyOf completions; one of two pending events triggered, the other left pending."""
    pending = []

    def waiter(env):
        for _ in range(num):
            e1, e2 = env.event(), env.event()
            pending.append((e1, e2))
            # Parks here: neither event is triggered yet.
            yield env.any_of([e1, e2])

    def releaser(env):
        for _ in range(num):
            # timeout(1) ensures waiter has parked on any_of before events fire.
            yield env.timeout(1)
            e1, e2 = pending.pop(0)
            # Only e1 is triggered; any_of completes on the first triggered event.
            e1.succeed()

    env = simpy.Environment()
    env.process(waiter(env))
    env.process(releaser(env))
    env.run()


BENCHMARKS = [
    ("AllOf",                               bench_allof),
    ("AllOf (blocking)",                    bench_allof_async),
    ("AnyOf",                               bench_anyof),
    ("AnyOf (blocking)",                    bench_anyof_async),
    ("Barrier (via Event)",                 bench_barrier),
    ("Container",                           bench_container),
    ("Container (float amounts)",           bench_container_float),
    ("Environment.run(until=)",             bench_run_until),
    ("Event",                               bench_event),
    ("Event (fail)",                        bench_event_fail),
    ("Interrupt",                           bench_interrupt),
    ("Interrupt (with cause)",              bench_interrupt_with_cause),
    ("PreemptiveResource",                  bench_preemptive),
    ("PreemptiveResource (cause fields)",   bench_preempted_cause),
    ("PreemptiveResource (no-preempt)",     bench_preemptive_no_preempt),
    ("PriorityStore",                       bench_priority_queue),
    ("Process",                             bench_process),
    ("Resource (contention)",               bench_resource_contention),
    ("Resource (context manager)",          bench_resource_context_manager),
    ("Resource (multi-capacity)",           bench_resource_multi_capacity),
    ("Resource (uncontended)",              bench_resource_uncontended),
    ("Store",                               bench_store),
    ("Store (FIFO queue)",                  bench_queue),
    ("Store (blocking get)",                bench_queue_blocking_get),
    ("Store (blocking put)",                bench_queue_blocking_put),
    ("Store (filtered get)",                bench_store_filtered_get),
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
    parser = argparse.ArgumentParser(description="Benchmark simpy features.")
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
            print(f"# simpy version {simpy_version}\n", file=out)
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
