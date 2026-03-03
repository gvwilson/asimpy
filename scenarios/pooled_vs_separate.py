"""Pooled vs. separate queues: one shared line beats multiple dedicated lines."""

import random
import statistics

from asimpy import Environment, Process, Resource

SIM_TIME = 100_000
ARRIVAL_RATE = 1.8  # total arrivals per time unit across both systems
SERVICE_RATE = 1.0  # per server
N_SERVERS = 2
SEED = 42

# Utilization per server: rho = arrival_rate / (n_servers * service_rate)
RHO = ARRIVAL_RATE / (N_SERVERS * SERVICE_RATE)


class Customer(Process):
    def init(self, server: Resource, sojourn_times: list):
        self.server = server
        self.sojourn_times = sojourn_times

    async def run(self):
        arrival = self.now
        async with self.server:
            await self.timeout(random.expovariate(SERVICE_RATE))
        self.sojourn_times.append(self.now - arrival)


class PooledArrivals(Process):
    """All customers join one shared queue feeding N_SERVERS servers."""

    def init(self, arrival_rate: float, server: Resource, sojourn_times: list):
        self.arrival_rate = arrival_rate
        self.server = server
        self.sojourn_times = sojourn_times

    async def run(self):
        while True:
            await self.timeout(random.expovariate(self.arrival_rate))
            Customer(self._env, self.server, self.sojourn_times)


class SeparateArrivals(Process):
    """Each customer randomly picks one of two dedicated servers and cannot switch."""

    def init(self, arrival_rate: float, servers: list[Resource], sojourn_times: list):
        self.arrival_rate = arrival_rate
        self.servers = servers
        self.sojourn_times = sojourn_times

    async def run(self):
        while True:
            await self.timeout(random.expovariate(self.arrival_rate))
            server = random.choice(self.servers)
            Customer(self._env, server, self.sojourn_times)


def run_pooled(arrival_rate: float = ARRIVAL_RATE, seed: int = SEED) -> float:
    random.seed(seed)
    sojourn_times: list[float] = []
    env = Environment()
    shared_server = Resource(env, capacity=N_SERVERS)
    PooledArrivals(env, arrival_rate, shared_server, sojourn_times)
    env.run(until=SIM_TIME)
    return statistics.mean(sojourn_times)


def run_separate(arrival_rate: float = ARRIVAL_RATE, seed: int = SEED) -> float:
    random.seed(seed)
    sojourn_times: list[float] = []
    env = Environment()
    servers = [Resource(env, capacity=1) for _ in range(N_SERVERS)]
    SeparateArrivals(env, arrival_rate, servers, sojourn_times)
    env.run(until=SIM_TIME)
    return statistics.mean(sojourn_times)


print(f"Arrival rate: {ARRIVAL_RATE}, service rate per server: {SERVICE_RATE}")
print(f"Number of servers: {N_SERVERS}, utilization rho = {RHO:.2f}")
print()

pooled_W = run_pooled()
separate_W = run_separate()

print(f"Mean sojourn time — pooled (single queue):  {pooled_W:.3f}")
print(f"Mean sojourn time — separate (pick a lane): {separate_W:.3f}")
print(f"Separate queues are {separate_W / pooled_W:.2f}x slower than pooled")
print()

# Show the effect across several utilization levels
print(f"{'rho':>6}  {'Pooled W':>10}  {'Separate W':>12}  {'Ratio':>7}")
print("-" * 44)
for rho in [0.5, 0.6, 0.7, 0.8, 0.9]:
    rate = rho * N_SERVERS * SERVICE_RATE
    pw = run_pooled(arrival_rate=rate)
    sw = run_separate(arrival_rate=rate)
    print(f"{rho:>6.2f}  {pw:>10.3f}  {sw:>12.3f}  {sw / pw:>7.2f}x")
