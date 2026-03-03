"""Tandem Queue Blocking: variability at Stage 1 starves Stage 2."""

import random

from asimpy import Environment, Process, Queue

SIM_TIME = 50_000
ARRIVAL_RATE = 0.8  # jobs per time unit
MEAN_SERVICE = 1.0  # mean service time at each stage (rho = 0.8)
SEED = 42


def high_variance_service() -> float:
    """Hyperexponential: 80% short (mean 0.2), 20% long (mean 4.5).
    Overall mean ≈ 0.8*0.2 + 0.2*4.5 = 0.16 + 0.90 = 1.06 ≈ MEAN_SERVICE."""
    if random.random() < 0.80:
        return random.expovariate(5.0)  # mean 0.2
    return random.expovariate(1.0 / 4.5)  # mean 4.5


def low_variance_service() -> float:
    """Deterministic: exactly MEAN_SERVICE every time (zero variance)."""
    return MEAN_SERVICE


class Source(Process):
    """Generates raw jobs into the first buffer."""

    def init(self, buffer: Queue):
        self.buffer = buffer

    async def run(self):
        jid = 0
        while True:
            await self.timeout(random.expovariate(ARRIVAL_RATE))
            await self.buffer.put(jid)
            jid += 1


class Stage1(Process):
    """Pulls jobs from input, processes them (high variance), pushes to middle buffer."""

    def init(self, inp: Queue, out: Queue, idle_tally: list):
        self.inp = inp
        self.out = out
        self.idle_tally = idle_tally

    async def run(self):
        while True:
            idle_start = self.now
            job = await self.inp.get()
            self.idle_tally.append(self.now - idle_start)  # wait for input
            await self.timeout(high_variance_service())
            await self.out.put(job)  # may block if buffer full


class Stage2(Process):
    """Pulls jobs from middle buffer, processes them (deterministic), records idle time."""

    def init(self, inp: Queue, idle_tally: list, completions: list):
        self.inp = inp
        self.idle_tally = idle_tally
        self.completions = completions

    async def run(self):
        while True:
            idle_start = self.now
            await self.inp.get()
            idle = self.now - idle_start
            self.idle_tally.append(idle)
            await self.timeout(low_variance_service())
            self.completions.append(self.now)


def simulate(buffer_capacity: int, seed: int = SEED) -> dict:
    random.seed(seed)
    env = Environment()
    input_q = Queue(env)  # unlimited input queue
    middle_q = Queue(env, max_capacity=buffer_capacity)

    s2_idle: list[float] = []
    completions: list[float] = []

    Source(env, input_q)
    Stage1(env, input_q, middle_q, [])
    Stage2(env, middle_q, s2_idle, completions)

    env.run(until=SIM_TIME)

    n = len(completions)
    idle_total = sum(s2_idle)
    return {
        "buffer_capacity": buffer_capacity,
        "throughput": n / SIM_TIME,
        "stage2_idle_frac": idle_total / SIM_TIME,
        "n_completed": n,
    }


print("Tandem Queue: high-variance Stage 1 starves low-variance Stage 2")
print(f"  Arrival rate: {ARRIVAL_RATE}, mean service per stage: {MEAN_SERVICE}")
print("  Stage 1: hyperexponential (high variance)")
print("  Stage 2: deterministic (zero variance)")
print()
print(f"  {'Buffer K':>8}  {'Throughput':>12}  {'Stage2 Idle %':>14}")
print("  " + "-" * 40)

for k in [1, 2, 3, 5, 8, 13, 21]:
    r = simulate(buffer_capacity=k)
    print(f"  {k:>8}  {r['throughput']:>12.4f}  {100 * r['stage2_idle_frac']:>13.1f}%")

print()
print("  Theoretical Stage 2 idle fraction with unlimited buffer ≈ 0%")
print("  (both stages have equal mean service rate, so Stage 2 is never idle")
print("   in steady state — but variability at Stage 1 starves it in practice)")
