"""
Sample size for the due-date test.

Two-sided test, equal groups, independent customers, normal approximation
using Cohen's h. I size for both measures, but plan the test on the
decision measure (first payment collected by day 60), not on on-time.

Run from the project root:  python src/power_analysis.py
"""

import math
from statistics import NormalDist

ALPHA = 0.05
POWER = 0.80
NORMAL = NormalDist()

# Baselines from the control group in the simulation.
BASELINES = {
    "first payment collected by day 60 (decision measure)": 0.9037,
    "on time vs own due date (supporting)": 0.72,
}
LIFTS = (0.02, 0.03, 0.05)


def required_per_arm(p0, absolute_lift, alpha=ALPHA, power=POWER):
    """Customers needed in EACH group to detect the lift."""
    p1 = p0 + absolute_lift
    if not (0 < p0 < 1 and 0 < p1 < 1):
        raise ValueError("Probabilities must be between 0 and 1")
    h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p0))
    z_alpha = NORMAL.inv_cdf(1 - alpha / 2)
    z_power = NORMAL.inv_cdf(power)
    return math.ceil(2 * ((z_alpha + z_power) / h) ** 2)


if __name__ == "__main__":
    print("Two-sided alpha 5%, 80% power, independent customers")
    for name, base in BASELINES.items():
        print(f"\n{name}, baseline {base:.1%}")
        print("lift (pts) | per group | total")
        for lift in LIFTS:
            n = required_per_arm(base, lift)
            print(f"{lift * 100:>10.0f} | {n:>9,} | {2 * n:>6,}")
