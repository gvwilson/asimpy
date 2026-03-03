"""Late Merge (Zipper Merge): using both lanes until the pinch point beats early merging.

Key insight: "polite" early merging halves the available pre-merge buffer,
causing more cars to be turned away and reducing throughput.
"""

import random

from asimpy import Environment, Event, Process, Queue

ARRIVAL_RATE = 1.85  # total cars per time unit
MERGE_RATE = 2.0  # cars the merge bottleneck can process per time unit
LANE_CAPACITY = 10  # pre-merge buffer size per lane
SIM_TIME = 30_000
SEED = 42

# Utilisation at merge: rho = ARRIVAL_RATE / MERGE_RATE = 0.925
RHO = ARRIVAL_RATE / MERGE_RATE


class EarlyMergeCar(Process):
    """
    Polite driver: joins lane 1 as soon as they see the sign.
    Lane 1 has capacity K = LANE_CAPACITY; lane 2 is unused.
    Total available buffer = LANE_CAPACITY.
    """

    def init(self, lane: Queue, sojourn_times: list, blocked: list):
        self.lane = lane
        self.sojourn_times = sojourn_times
        self.blocked = blocked

    async def run(self):
        arrival = self.now
        if self.lane.is_full():
            self.blocked.append(1)
            return
        done = Event(self._env)
        await self.lane.put((arrival, done))
        await done
        self.sojourn_times.append(self.now - arrival)


class LateMergeCar(Process):
    """
    Zipper driver: stays in whichever lane is shorter until the merge point.
    Two lanes each have capacity K = LANE_CAPACITY.
    Total available buffer = 2 × LANE_CAPACITY.
    """

    def init(self, lane1: Queue, lane2: Queue, sojourn_times: list, blocked: list):
        self.lane1 = lane1
        self.lane2 = lane2
        self.sojourn_times = sojourn_times
        self.blocked = blocked

    async def run(self):
        arrival = self.now
        # Pick the shorter lane
        target = (
            self.lane1
            if len(self.lane1._items) <= len(self.lane2._items)
            else self.lane2
        )
        if target.is_full():
            self.blocked.append(1)
            return
        done = Event(self._env)
        await target.put((arrival, done))
        await done
        self.sojourn_times.append(self.now - arrival)


class MergeServer(Process):
    """Processes cars from lane(s) through the bottleneck, then signals each car."""

    def init(self, lanes: list[Queue], zipper: bool):
        self.lanes = lanes
        self.zipper = zipper
        self._turn = 0

    async def run(self):
        while True:
            if self.zipper:
                served = False
                for _ in range(len(self.lanes)):
                    idx = self._turn % len(self.lanes)
                    self._turn += 1
                    if not self.lanes[idx].is_empty():
                        _, arrival, done = (self.now,) + (await self.lanes[idx].get())
                        await self.timeout(random.expovariate(MERGE_RATE))
                        done.succeed()
                        served = True
                        break
                if not served:
                    await self.timeout(0.05)
            else:
                _, arrival, done = (self.now,) + (await self.lanes[0].get())
                await self.timeout(random.expovariate(MERGE_RATE))
                done.succeed()


class ArrivalStream(Process):
    def init(
        self, lanes: list[Queue], sojourn_times: list, blocked: list, zipper: bool
    ):
        self.lanes = lanes
        self.sojourn_times = sojourn_times
        self.blocked = blocked
        self.zipper = zipper

    async def run(self):
        while True:
            await self.timeout(random.expovariate(ARRIVAL_RATE))
            if self.zipper:
                LateMergeCar(
                    self._env,
                    self.lanes[0],
                    self.lanes[1],
                    self.sojourn_times,
                    self.blocked,
                )
            else:
                EarlyMergeCar(
                    self._env, self.lanes[0], self.sojourn_times, self.blocked
                )


def run_scenario(zipper: bool, seed: int = SEED) -> dict:
    random.seed(seed)
    env = Environment()
    sojourn_times: list[float] = []
    blocked: list[int] = []

    if zipper:
        lanes = [
            Queue(env, max_capacity=LANE_CAPACITY),
            Queue(env, max_capacity=LANE_CAPACITY),
        ]
    else:
        lanes = [Queue(env, max_capacity=LANE_CAPACITY)]

    ArrivalStream(env, lanes, sojourn_times, blocked, zipper)
    MergeServer(env, lanes, zipper)
    env.run(until=SIM_TIME)

    total = len(sojourn_times) + len(blocked)
    return {
        "throughput": len(sojourn_times) / SIM_TIME,
        "blocked_pct": 100.0 * len(blocked) / total if total else 0.0,
        "mean_sojourn": sum(sojourn_times) / len(sojourn_times)
        if sojourn_times
        else 0.0,
        "total_buffer": LANE_CAPACITY * (2 if zipper else 1),
    }


print("Late (Zipper) Merge vs. Early (Courtesy) Merge")
print(f"  Arrival rate: {ARRIVAL_RATE}/unit, merge service rate: {MERGE_RATE}/unit")
print(f"  Utilisation rho = {RHO:.3f},  per-lane buffer = {LANE_CAPACITY}")
print()

early = run_scenario(zipper=False)
late = run_scenario(zipper=True)

print(f"  {'Metric':<22}  {'Early merge':>12}  {'Late merge':>12}")
print("  " + "-" * 52)
print(
    f"  {'Total buffer (cars)':<22}  {early['total_buffer']:>12}  "
    f"{late['total_buffer']:>12}"
)
print(
    f"  {'Throughput (cars/unit)':<22}  {early['throughput']:>12.4f}  "
    f"{late['throughput']:>12.4f}"
)
print(
    f"  {'Blocked cars %':<22}  {early['blocked_pct']:>11.1f}%  "
    f"{late['blocked_pct']:>11.1f}%"
)
print(
    f"  {'Mean sojourn time':<22}  {early['mean_sojourn']:>12.3f}  "
    f"{late['mean_sojourn']:>12.3f}"
)
print()
print(
    f"  Late merge has {late['throughput'] / early['throughput']:.3f}x the throughput "
    f"and {early['blocked_pct'] / late['blocked_pct']:.1f}x fewer blocked cars."
)
print()
print("  Effect of lane buffer size on early-merge blocking rate:")
print(f"  {'Buffer K':>8}  {'Early blocked %':>16}  {'Late blocked %':>15}")
print("  " + "-" * 44)
for k in [5, 10, 15, 20, 30]:
    r_e = run_scenario(zipper=False, seed=SEED)
    r_l = run_scenario(zipper=True, seed=SEED)

    # Quick re-run with custom capacity
    random.seed(SEED)
    env2 = Environment()
    st2: list[float] = []
    bl2: list[int] = []
    lns2 = [Queue(env2, max_capacity=k)]
    ArrivalStream(env2, lns2, st2, bl2, False)
    MergeServer(env2, lns2, False)
    env2.run(until=SIM_TIME)
    t2 = len(st2) + len(bl2)
    ep = 100.0 * len(bl2) / t2 if t2 else 0.0

    random.seed(SEED)
    env3 = Environment()
    st3: list[float] = []
    bl3: list[int] = []
    lns3 = [Queue(env3, max_capacity=k), Queue(env3, max_capacity=k)]
    ArrivalStream(env3, lns3, st3, bl3, True)
    MergeServer(env3, lns3, True)
    env3.run(until=SIM_TIME)
    t3 = len(st3) + len(bl3)
    lp = 100.0 * len(bl3) / t3 if t3 else 0.0
    print(f"  {k:>8}  {ep:>15.1f}%  {lp:>14.1f}%")
