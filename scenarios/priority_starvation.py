"""Priority Starvation: high-priority load can cause low-priority jobs to wait forever.

Demonstrates two effects:
1. Static priority: as hi-priority utilization grows, lo-priority waits diverge.
2. Aging: the server promotes a lo-priority job once it has waited long enough,
   preventing starvation at the cost of occasional hi-priority delay bursts.
"""

import random
import statistics

from asimpy import Environment, Process, Queue

SIM_TIME = 30_000
SERVICE_RATE_HI = 2.0  # mean service time = 0.5 for hi-priority
SERVICE_RATE_LO = 1.0  # mean service time = 1.0 for lo-priority
ARRIVAL_RATE_LO = 0.2  # rho_lo = 0.2 / 1.0 = 0.20  (fixed)
AGING_THRESHOLD = 15.0  # lo-priority promoted if waiting longer than this
SEED = 42


class StaticPriorityServer(Process):
    """
    Non-preemptive static priority.
    hi_q: holds (arrival_time, service_time) for high-priority jobs.
    lo_q: holds (arrival_time, service_time) for low-priority jobs.
    Always drains hi_q first.
    """

    def init(self, hi_q: Queue, lo_q: Queue, sojourn_hi: list, sojourn_lo: list):
        self.hi_q = hi_q
        self.lo_q = lo_q
        self.sojourn_hi = sojourn_hi
        self.sojourn_lo = sojourn_lo

    async def _serve(self, arrival: float, svc: float, record: list):
        await self.timeout(svc)
        record.append(self.now - arrival)

    async def run(self):
        while True:
            if not self.hi_q.is_empty():
                arrival, svc = await self.hi_q.get()
                await self._serve(arrival, svc, self.sojourn_hi)
            elif not self.lo_q.is_empty():
                arrival, svc = await self.lo_q.get()
                await self._serve(arrival, svc, self.sojourn_lo)
            else:
                await self.timeout(0.01)  # idle: poll briefly


class AgingServer(Process):
    """
    Non-preemptive priority with aging: a lo-priority job that has waited
    longer than AGING_THRESHOLD is promoted ahead of fresh hi-priority jobs.
    """

    def init(self, hi_q: Queue, lo_q: Queue, sojourn_hi: list, sojourn_lo: list):
        self.hi_q = hi_q
        self.lo_q = lo_q
        self.sojourn_hi = sojourn_hi
        self.sojourn_lo = sojourn_lo

    async def run(self):
        while True:
            # Check if oldest lo-priority job has aged past threshold
            lo_aged = (
                not self.lo_q.is_empty()
                and self.now - self.lo_q._items[0][0] >= AGING_THRESHOLD
            )
            if lo_aged:
                arrival, svc = await self.lo_q.get()
                await self.timeout(svc)
                self.sojourn_lo.append(self.now - arrival)
            elif not self.hi_q.is_empty():
                arrival, svc = await self.hi_q.get()
                await self.timeout(svc)
                self.sojourn_hi.append(self.now - arrival)
            elif not self.lo_q.is_empty():
                arrival, svc = await self.lo_q.get()
                await self.timeout(svc)
                self.sojourn_lo.append(self.now - arrival)
            else:
                await self.timeout(0.01)


class HiSource(Process):
    def init(self, rate: float, q: Queue):
        self.rate = rate
        self.q = q

    async def run(self):
        while True:
            await self.timeout(random.expovariate(self.rate))
            svc = random.expovariate(SERVICE_RATE_HI)
            await self.q.put((self.now, svc))


class LoSource(Process):
    def init(self, q: Queue):
        self.q = q

    async def run(self):
        while True:
            await self.timeout(random.expovariate(ARRIVAL_RATE_LO))
            svc = random.expovariate(SERVICE_RATE_LO)
            await self.q.put((self.now, svc))


def simulate(
    arrival_rate_hi: float, use_aging: bool, seed: int = SEED
) -> tuple[list, list]:
    random.seed(seed)
    env = Environment()
    hi_q: Queue = Queue(env)
    lo_q: Queue = Queue(env)
    sojourn_hi: list[float] = []
    sojourn_lo: list[float] = []
    HiSource(env, arrival_rate_hi, hi_q)
    LoSource(env, lo_q)
    if use_aging:
        AgingServer(env, hi_q, lo_q, sojourn_hi, sojourn_lo)
    else:
        StaticPriorityServer(env, hi_q, lo_q, sojourn_hi, sojourn_lo)
    env.run(until=SIM_TIME)
    return sojourn_hi, sojourn_lo


def mean_or_na(lst: list) -> str:
    return f"{statistics.mean(lst):.2f}" if lst else "  N/A"


print("Priority Starvation")
print(
    f"  lo-priority: arrival rate {ARRIVAL_RATE_LO}, "
    f"mean service {1 / SERVICE_RATE_LO:.1f}, rho_lo = {ARRIVAL_RATE_LO / SERVICE_RATE_LO:.2f}"
)
print(f"  Aging threshold: {AGING_THRESHOLD} time units")
print()

# Part 1: sweep hi-priority utilization with static priority
print("Part 1 — Static priority: effect of hi-priority load on lo-priority wait")
print(f"  {'rho_hi':>7}  {'rho_total':>10}  {'Mean W_hi':>10}  {'Mean W_lo':>10}")
print("  " + "-" * 46)
for rho_hi in [0.10, 0.20, 0.40, 0.60, 0.70, 0.80]:
    rate_hi = rho_hi * SERVICE_RATE_HI
    hi, lo = simulate(rate_hi, use_aging=False)
    rho_total = rho_hi + ARRIVAL_RATE_LO / SERVICE_RATE_LO
    print(
        f"  {rho_hi:>7.2f}  {rho_total:>10.2f}  "
        f"{mean_or_na(hi):>10}  {mean_or_na(lo):>10}"
    )

print()

# Part 2: static vs. aging at a fixed hi load where starvation is visible
FIXED_RHO_HI = 0.70
rate_hi = FIXED_RHO_HI * SERVICE_RATE_HI
rho_total = FIXED_RHO_HI + ARRIVAL_RATE_LO / SERVICE_RATE_LO

print(
    f"Part 2 — Static vs. aging at rho_hi={FIXED_RHO_HI:.2f}, rho_total={rho_total:.2f}"
)
print()

hi_static, lo_static = simulate(rate_hi, use_aging=False)
hi_aging, lo_aging = simulate(rate_hi, use_aging=True)


def pct(lst: list, p: float) -> str:
    if not lst:
        return "N/A"
    idx = int(p * len(lst))
    return f"{sorted(lst)[idx]:.2f}"


print("  Static priority (hi always beats lo):")
print(
    f"    Hi: n={len(hi_static):<5} mean={mean_or_na(hi_static):>6}  "
    f"p95={pct(hi_static, 0.95):>6}  p99={pct(hi_static, 0.99):>6}"
)
print(
    f"    Lo: n={len(lo_static):<5} mean={mean_or_na(lo_static):>6}  "
    f"p95={pct(lo_static, 0.95):>6}  p99={pct(lo_static, 0.99):>6}"
)
print()
print(f"  Aging (lo promoted after {AGING_THRESHOLD:.0f} units):")
print(
    f"    Hi: n={len(hi_aging):<5} mean={mean_or_na(hi_aging):>6}  "
    f"p95={pct(hi_aging, 0.95):>6}  p99={pct(hi_aging, 0.99):>6}"
)
print(
    f"    Lo: n={len(lo_aging):<5} mean={mean_or_na(lo_aging):>6}  "
    f"p95={pct(lo_aging, 0.95):>6}  p99={pct(lo_aging, 0.99):>6}"
)
print()
if lo_static and lo_aging:
    print(
        f"  Aging caps max lo-priority wait at ~{AGING_THRESHOLD:.0f} units, "
        f"reducing p99 from {pct(lo_static, 0.99)} to {pct(lo_aging, 0.99)}."
    )
