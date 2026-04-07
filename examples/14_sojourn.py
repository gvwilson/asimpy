"""Example: measuring sojourn time components across utilization levels."""

import random
import statistics
from pathlib import Path

import altair as alt
import polars as pl
from prettytable import PrettyTable, TableStyle

from asimpy import Environment, Process, Resource

SEED = 192          # random seed for reproducibility
SIM_TIME = 20_000   # simulated time units per scenario
SERVICE_RATE = 1.0  # exponential service rate (mu); mean service time = 1/mu
SAMPLE_INTERVAL = 1 # sim-time units between Monitor samples
RHO_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]  # utilization levels
CHART_PATH = Path(__file__).parent.parent / "pages" / "tutorial" / "14_sojourn.svg"


class Customer(Process):
    def init(self, server, in_system, sojourn_times, wait_times):
        self.server = server
        self.in_system = in_system
        self.sojourn_times = sojourn_times
        self.wait_times = wait_times

    async def run(self):
        arrival = self.now
        self.in_system[0] += 1
        async with self.server:
            service_start = self.now
            await self.timeout(random.expovariate(SERVICE_RATE))
        self.in_system[0] -= 1
        self.sojourn_times.append(self.now - arrival)
        self.wait_times.append(service_start - arrival)


class Arrivals(Process):
    def init(self, rate, server, in_system, sojourn_times, wait_times):
        self.rate = rate
        self.server = server
        self.in_system = in_system
        self.sojourn_times = sojourn_times
        self.wait_times = wait_times

    async def run(self):
        while True:
            await self.timeout(random.expovariate(self.rate))
            Customer(self._env, self.server, self.in_system, self.sojourn_times, self.wait_times)


class Monitor(Process):
    def init(self, in_system, samples):
        self.in_system = in_system
        self.samples = samples

    async def run(self):
        while True:
            self.samples.append(self.in_system[0])
            await self.timeout(SAMPLE_INTERVAL)


def simulate(rho):
    rate = rho * SERVICE_RATE
    env = Environment()
    server = Resource(env, capacity=1)
    in_system = [0]
    sojourn_times = []
    wait_times = []
    samples = []
    Arrivals(env, rate, server, in_system, sojourn_times, wait_times)
    Monitor(env, in_system, samples)
    env.run(until=SIM_TIME)
    mean_W = statistics.mean(sojourn_times)
    mean_Wq = statistics.mean(wait_times)
    mean_Ws = mean_W - mean_Wq
    mean_L = statistics.mean(samples)
    lam = len(sojourn_times) / SIM_TIME
    theory_W = 1.0 / (SERVICE_RATE * (1.0 - rho))
    return {
        "rho": rho,
        "mean_Wq": round(mean_Wq, 4),
        "mean_Ws": round(mean_Ws, 4),
        "mean_W": round(mean_W, 4),
        "theory_W": round(theory_W, 4),
        "L_sampled": round(mean_L, 4),
        "L_little": round(lam * mean_W, 4),
    }


def main():
    random.seed(SEED)
    rows = [simulate(rho) for rho in RHO_VALUES]

    table = PrettyTable(list(rows[0].keys()))
    for row in rows:
        table.add_row(list(row.values()))
    table.set_style(TableStyle.MARKDOWN)
    print(table)

    df = pl.DataFrame(rows)
    long_df = df.select(["rho", "mean_Wq", "mean_Ws"]).unpivot(
        on=["mean_Wq", "mean_Ws"],
        index="rho",
        variable_name="component",
        value_name="time",
    )
    chart = (
        alt.Chart(long_df)
        .mark_area()
        .encode(
            x=alt.X("rho:Q", title="Utilization (rho)"),
            y=alt.Y("time:Q", title="Mean time", stack="zero"),
            color=alt.Color("component:N", title="Component"),
        )
        .properties(title="Sojourn Time Components: Wq (waiting) + Ws (service) = W")
    )
    chart.save(str(CHART_PATH))


if __name__ == "__main__":
    main()
