"""Two-sided, equal-allocation normal approximation for two independent proportions."""
import math
from statistics import NormalDist

BASELINE = 0.72
ALPHA = 0.05
POWER = 0.80
NORMAL = NormalDist()

def required_per_arm(p0: float, absolute_lift: float, alpha: float = ALPHA, power: float = POWER) -> int:
    """Cohen's h with normal-approximation independent two-proportions power."""
    p1 = p0 + absolute_lift
    if not (0 < p0 < 1 and 0 < p1 < 1):
        raise ValueError('Probabilities must be within (0,1)')
    h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p0))
    z_alpha = NORMAL.inv_cdf(1 - alpha / 2)
    z_power = NORMAL.inv_cdf(power)
    # Cohen's h approximation for independent groups with equal sample sizes.
    return math.ceil(2 * ((z_alpha + z_power) / h) ** 2)

if __name__ == '__main__':
    print('Baseline 72%, two-sided alpha 5%, 80% power, independent customers')
    print('MDE (pp) | n per arm | total')
    for lift in (0.02, 0.03, 0.05):
        n = required_per_arm(BASELINE, lift)
        print(f'{lift*100:>7.0f} | {n:>9,} | {2*n:>5,}')
