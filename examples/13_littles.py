"""Example: verifying Little's Law."""

import random
import statistics

from prettytable import PrettyTable, TableStyle

from asimpy import Environment, Process, Resource

SEED = 192                  # random seed for reproducibility
SIM_TIME = 1000             # simulated time units per scenario
SAMPLE_INTERVAL = 1         # sim-time units between Monitor samples
SERVICE_RATE = 1.0          # exponential service rate (mu) for random service


class RandomCustomer(Process):
    def init(self, server, in_system, sojourn_times):
        self.server = server
        self.in_system = in_system
        self.sojourn_times = sojourn_times

    async def run(self):
        arrival = self.now
        self.in_system[0] += 1
        async with self.server:
            await self.timeout(random.expovariate(SERVICE_RATE))
        self.in_system[0] -= 1
        self.sojourn_times.append(self.now - arrival)


class RandomArrivals(Process):
    def init(self, rate, server, in_system, sojourn_times):
        self.rate = rate
        self.server = server
        self.in_system = in_system
        self.sojourn_times = sojourn_times

    async def run(self):
        while True:
            await self.timeout(random.expovariate(self.rate))
            RandomCustomer(self._env, self.server, self.in_system, self.sojourn_times)


class Monitor(Process):
    def init(self, in_system, samples):
        self.in_system = in_system
        self.samples = samples

    async def run(self):
        while True:
            self.samples.append(self.in_system[0])
            await self.timeout(SAMPLE_INTERVAL)


def run_scenario(lam, capacity):
    in_system = [0]
    sojourns = []
    samples = []
    env = Environment()
    server = Resource(env, capacity=capacity)
    RandomArrivals(env, lam, server, in_system, sojourns)
    Monitor(env, in_system, samples)
    env.run(until=SIM_TIME)
    L_direct = statistics.mean(samples)
    W = statistics.mean(sojourns)
    lam_obs = len(sojourns) / SIM_TIME
    L_little = lam_obs * W
    error = 100.0 * (L_little - L_direct) / L_direct
    return {
        "lambda": round(lam_obs, 3),
        "capacity": capacity,
        "W": round(W, 3),
        "L_direct": round(L_direct, 3),
        "L_little": round(L_little, 3),
        "error_%": round(error, 2),
    }


def main():
    random.seed(SEED)
    rows = []
    for lam in (0.5, 1.0, 1.5, 2.0, 2.5):
        for capacity in (2, 3, 4):
            rows.append(run_scenario(lam, capacity))

    table = PrettyTable(list(rows[0].keys()))
    table.align = "r"
    for row in rows:
        table.add_row(list(row.values()))
    table.set_style(TableStyle.MARKDOWN)
    print(table)


if __name__ == "__main__":
    main()
