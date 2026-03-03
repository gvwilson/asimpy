"""Convoy Effect: one slow job behind a FIFO gate delays many fast jobs."""

import random
import statistics

from asimpy import Environment, Process, Queue

ARRIVAL_RATE = 0.7  # jobs per unit time; < 1.0 so the system is stable
SIM_TIME = 50_000
SEED = 42

# Service-time distribution: mix of short and long jobs
SHORT_RATE = 4.0  # mean service = 0.25  (90 % of jobs)
LONG_RATE = 0.2  # mean service = 5.0   (10 % of jobs)
LONG_PROB = 0.10


def service_time() -> float:
    """Hyperexponential: mostly quick, occasionally very slow."""
    if random.random() < LONG_PROB:
        return random.expovariate(LONG_RATE)
    return random.expovariate(SHORT_RATE)


# Mean service time: 0.9*0.25 + 0.1*5 = 0.225 + 0.5 = 0.725
# Utilization rho ≈ 0.7 * 0.725 ≈ 0.508


class JobSource(Process):
    def init(self, job_queue: Queue, arrivals: dict, sjf: bool):
        self.job_queue = job_queue
        self.arrivals = arrivals
        self.sjf = sjf
        self._jid = 0

    async def run(self):
        while True:
            await self.timeout(random.expovariate(ARRIVAL_RATE))
            jid = self._jid
            self._jid += 1
            svc = service_time()
            self.arrivals[jid] = (self.now, svc)
            if self.sjf:
                # Priority queue: smaller service time = served sooner
                await self.job_queue.put((svc, jid))
            else:
                # FIFO: use arrival ID as key so insertion order is preserved
                await self.job_queue.put((jid, svc))


class Server(Process):
    def init(self, job_queue: Queue, arrivals: dict, sojourn_times: list, sjf: bool):
        self.job_queue = job_queue
        self.arrivals = arrivals
        self.sojourn_times = sojourn_times
        self.sjf = sjf

    async def run(self):
        while True:
            item = await self.job_queue.get()
            if self.sjf:
                svc, jid = item
            else:
                jid, svc = item
            await self.timeout(svc)
            arrival_time, _ = self.arrivals[jid]
            self.sojourn_times.append(self.now - arrival_time)


def simulate(sjf: bool, seed: int = SEED) -> dict:
    random.seed(seed)
    arrivals: dict[int, tuple[float, float]] = {}
    sojourn_times: list[float] = []
    env = Environment()
    q = Queue(env, priority=sjf)
    JobSource(env, q, arrivals, sjf)
    Server(env, q, arrivals, sojourn_times, sjf)
    env.run(until=SIM_TIME)
    return {
        "mean": statistics.mean(sojourn_times),
        "median": statistics.median(sojourn_times),
        "p95": sorted(sojourn_times)[int(0.95 * len(sojourn_times))],
        "p99": sorted(sojourn_times)[int(0.99 * len(sojourn_times))],
        "n": len(sojourn_times),
    }


fifo = simulate(sjf=False)
sjf = simulate(sjf=True)

print("Convoy Effect: FIFO vs. Shortest Job First (SJF)")
print()
print(
    f"  Arrival rate: {ARRIVAL_RATE}, estimated mean service: "
    f"{(1 - LONG_PROB) / SHORT_RATE + LONG_PROB / LONG_RATE:.3f}"
)
print(
    f"  Short jobs: {100 * (1 - LONG_PROB):.0f}% (mean {1 / SHORT_RATE:.2f}), "
    f"Long jobs: {100 * LONG_PROB:.0f}% (mean {1 / LONG_RATE:.1f})"
)
print()
print(f"  {'Metric':<12}  {'FIFO':>10}  {'SJF':>10}  {'Improvement':>12}")
print("  " + "-" * 50)
for metric in ("mean", "median", "p95", "p99"):
    ratio = fifo[metric] / sjf[metric]
    print(
        f"  {metric:<12}  {fifo[metric]:>10.3f}  {sjf[metric]:>10.3f}  {ratio:>11.2f}x"
    )
print()
print("  Note: SJF is optimal for mean sojourn time but requires")
print("  knowing job sizes in advance (not always possible in practice).")
