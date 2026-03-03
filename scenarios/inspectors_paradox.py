"""Inspector's Paradox: a random observer almost always arrives during a long gap."""

import random
import statistics

from asimpy import Environment, Process

SIM_TIME = 100_000
MEAN_HEADWAY = 10.0  # average time between buses
N_PASSENGERS = 20_000  # random-time passengers used for wait estimation
SEED = 42


class BusService(Process):
    """Generates buses and records their arrival times."""

    def init(self, mode: str, bus_arrivals: list):
        self.mode = mode
        self.bus_arrivals = bus_arrivals

    async def run(self):
        while True:
            if self.mode == "regular":
                # Deterministic: perfectly spaced, zero variance
                headway = MEAN_HEADWAY
            elif self.mode == "exponential":
                # Memoryless: headway ~ Exp(1/mean), high variance (CV=1)
                headway = random.expovariate(1.0 / MEAN_HEADWAY)
            elif self.mode == "clustered":
                # Bimodal: buses arrive in bursts (mean=10, high variance)
                headway = 2.0 if random.random() < 0.5 else 18.0
            else:
                raise ValueError(f"Unknown mode: {self.mode}")
            await self.timeout(headway)
            self.bus_arrivals.append(self.now)


def collect_buses(mode: str, seed: int = SEED) -> list[float]:
    random.seed(seed)
    bus_arrivals: list[float] = []
    env = Environment()
    BusService(env, mode, bus_arrivals)
    env.run(until=SIM_TIME)
    return bus_arrivals


def expected_wait(
    bus_arrivals: list[float], n: int = N_PASSENGERS, seed: int = SEED
) -> float:
    """Estimate mean passenger wait by sampling random arrival times."""
    rng = random.Random(seed + 1)
    max_t = bus_arrivals[-1]
    waits: list[float] = []
    for _ in range(n):
        t = rng.uniform(0.0, max_t * 0.95)
        # Find the first bus that arrives after t
        for b in bus_arrivals:
            if b > t:
                waits.append(b - t)
                break
    return statistics.mean(waits) if waits else 0.0


def headway_variance(bus_arrivals: list[float]) -> float:
    headways = [b - a for a, b in zip(bus_arrivals, bus_arrivals[1:])]
    return statistics.variance(headways) if len(headways) > 1 else 0.0


print("Inspector's Paradox")
print(
    f"  Mean headway: {MEAN_HEADWAY}  =>  naive expected wait = {MEAN_HEADWAY / 2:.1f}"
)
print()
print(
    f"  {'Mode':<14}  {'Var(headway)':>14}  {'Mean wait':>10}  {'Ratio to naive':>16}"
)
print("  " + "-" * 60)

for mode in ["regular", "exponential", "clustered"]:
    buses = collect_buses(mode)
    var_h = headway_variance(buses)
    mean_w = expected_wait(buses)
    naive = MEAN_HEADWAY / 2.0
    ratio = mean_w / naive
    print(f"  {mode:<14}  {var_h:>14.2f}  {mean_w:>10.3f}  {ratio:>15.2f}x")

print()
print("The Inspector's Paradox formula:")
print("  E[wait] = E[headway]/2 + Var[headway] / (2 * E[headway])")
print()

# Verify analytically for exponential case
# For Exp(1/mu): E[H]=mu, Var[H]=mu^2
# E[wait] = mu/2 + mu^2/(2*mu) = mu/2 + mu/2 = mu
mu = MEAN_HEADWAY
print(f"  Exponential (Var = E^2 = {mu**2:.1f}):")
print(
    f"    Predicted wait = {mu / 2:.1f} + {mu**2 / (2 * mu):.1f} = {mu:.1f}  (= full mean headway!)"
)

# Clustered: E=10, Var = E[(H - 10)^2] = 0.5*(2-10)^2 + 0.5*(18-10)^2 = 64
var_clustered = 0.5 * (2 - mu) ** 2 + 0.5 * (18 - mu) ** 2
print(f"  Clustered (Var = {var_clustered:.1f}):")
print(
    f"    Predicted wait = {mu / 2:.1f} + {var_clustered / (2 * mu):.1f} = {mu / 2 + var_clustered / (2 * mu):.1f}"
)
