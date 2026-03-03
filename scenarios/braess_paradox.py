"""Braess's Paradox: adding a road can make everyone's commute longer.

Uses a routing-game approach: cars depart in discrete waves and use logit
(softmax) routing, which converges smoothly to a Nash equilibrium.
The DES clock advances one unit per wave.
"""

import math
import random

from asimpy import Environment, Process

# Classic Braess network parameters
N_DRIVERS = 4000  # total drivers per wave (classic textbook scale)
CAPACITY = 100.0  # delay = n_cars / CAPACITY for congested links
CONST_DELAY = 45.0  # fixed delay on unconstrained links (AT and SB)
BETA = 0.5  # logit sensitivity (higher = closer to deterministic)
N_ROUNDS = 80  # waves to simulate
SEED = 42

# Equilibrium predictions:
# Without shortcut: 2000 on each route → t = 2000/100 + 45 = 65
# With shortcut:    4000 on SA+AB+BT   → t = 4000/100 + 4000/100 = 80 (worse!)


def route_times(n_top: int, n_bot: int, n_short: int) -> tuple[float, float, float]:
    n_sa = n_top + n_short
    n_bt = n_bot + n_short
    t_top = n_sa / CAPACITY + CONST_DELAY
    t_bot = CONST_DELAY + n_bt / CAPACITY
    t_short = n_sa / CAPACITY + n_bt / CAPACITY  # AB delay ≈ 0
    return t_top, t_bot, t_short


def logit_split(times: list[float]) -> list[float]:
    """Logit (softmax) route choice: P(r) ∝ exp(-beta * t_r)."""
    vals = [math.exp(-BETA * t) for t in times]
    total = sum(vals)
    return [v / total for v in vals]


class RoutingGame(Process):
    """
    Simulates N_ROUNDS waves of N_DRIVERS cars choosing routes via logit.
    Each wave advances the DES clock by one time unit.
    """

    def init(self, has_shortcut: bool, history: list):
        self.has_shortcut = has_shortcut
        self.history = history
        self._n_top = N_DRIVERS // 2
        self._n_bot = N_DRIVERS - N_DRIVERS // 2
        self._n_short = 0

    async def run(self):
        for _ in range(N_ROUNDS):
            await self.timeout(1.0)

            t_top, t_bot, t_short = route_times(self._n_top, self._n_bot, self._n_short)

            if self.has_shortcut:
                probs = logit_split([t_top, t_bot, t_short])
                self._n_top = round(N_DRIVERS * probs[0])
                self._n_bot = round(N_DRIVERS * probs[1])
                self._n_short = N_DRIVERS - self._n_top - self._n_bot
            else:
                probs = logit_split([t_top, t_bot])
                self._n_top = round(N_DRIVERS * probs[0])
                self._n_bot = N_DRIVERS - self._n_top
                self._n_short = 0

            t_top2, t_bot2, t_short2 = route_times(
                self._n_top, self._n_bot, self._n_short
            )
            mean_t = (
                self._n_top * t_top2 + self._n_bot * t_bot2 + self._n_short * t_short2
            ) / N_DRIVERS
            self.history.append(
                {
                    "round": self.now,
                    "n_top": self._n_top,
                    "n_bot": self._n_bot,
                    "n_short": self._n_short,
                    "t_top": t_top2,
                    "t_bot": t_bot2,
                    "t_short": t_short2,
                    "mean": mean_t,
                }
            )


def simulate(has_shortcut: bool) -> list:
    random.seed(SEED)
    history: list = []
    env = Environment()
    RoutingGame(env, has_shortcut, history)
    env.run()
    return history


hist_no = simulate(has_shortcut=False)
hist_yes = simulate(has_shortcut=True)


def fmt(h: dict, shortcut: bool) -> str:
    if shortcut:
        return (
            f"  {h['round']:>6.0f}  {h['n_top']:>6}  {h['n_bot']:>6}  "
            f"{h['n_short']:>8}  {h['mean']:>8.2f}"
        )
    return f"  {h['round']:>6.0f}  {h['n_top']:>6}  {h['n_bot']:>6}  {h['mean']:>8.2f}"


print("Braess's Paradox")
print(
    f"  {N_DRIVERS} drivers, congested link delay = n/capacity (capacity={CAPACITY:.0f})"
)
print(f"  Constant link delay = {CONST_DELAY} (links AT and SB)")
print()

print("Without shortcut — convergence to equilibrium:")
print(f"  {'Round':>6}  {'n_top':>6}  {'n_bot':>6}  {'Mean T':>8}")
for h in list(hist_no[::10]) + [hist_no[-1]]:
    print(fmt(h, shortcut=False))

print()
print("With shortcut — convergence to equilibrium:")
print(f"  {'Round':>6}  {'n_top':>6}  {'n_bot':>6}  {'n_short':>8}  {'Mean T':>8}")
for h in list(hist_yes[::10]) + [hist_yes[-1]]:
    print(fmt(h, shortcut=True))

print()
eq_no = hist_no[-1]["mean"]
eq_yes = hist_yes[-1]["mean"]
print(f"  Nash equilibrium travel time WITHOUT shortcut: {eq_no:.2f}")
print(f"  Nash equilibrium travel time WITH shortcut:    {eq_yes:.2f}")
print(
    f"  Adding the shortcut increased travel time by "
    f"{eq_yes - eq_no:.2f} units "
    f"({100 * (eq_yes / eq_no - 1):.1f}% worse for every driver)"
)

print()
print("Theoretical predictions:")
n_half = N_DRIVERS / 2
t_theory_no = n_half / CAPACITY + CONST_DELAY
t_theory_yes = N_DRIVERS / CAPACITY + N_DRIVERS / CAPACITY
print(
    f"  Without shortcut (50/50 split): "
    f"{n_half:.0f}/{CAPACITY:.0f} + {CONST_DELAY:.0f} = {t_theory_no:.2f}"
)
print(
    f"  With shortcut (all on SA→AB→BT): "
    f"{N_DRIVERS}/{CAPACITY:.0f} + {N_DRIVERS}/{CAPACITY:.0f} = {t_theory_yes:.2f}"
)
