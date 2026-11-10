"""
Settlement break-even: when does a settlement beat normal collections?

Three numbers, with different denominators:
    acceptance rate  = accepted offers / offers made
    completion rate  = completed settlements / ACCEPTED offers   (this script solves for this one)
    overall recovery = what the whole offered group pays back

Costs fall at different times, so I split them:
    setup cost       paid as soon as the customer accepts, whatever happens next
    completion cost  paid only when the settlement is completed
    failure cost     extra collections cost when an accepted settlement falls through

For a customer who accepts:
    with settlement    = completion x (settlement share - completion cost)
                       + (1 - completion) x (recovery if it fails - failure cost)
                       - setup cost
    without settlement = expected recovery through normal collections

Solving "with = without" gives the break-even completion rate.

Every input is an assumption, as a share of the balance owed.
Credit Risk would replace them with real data. Run from the project root:
    python src/settlement_breakeven.py
"""

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "outputs"
OUT.mkdir(exist_ok=True)

SETTLEMENT_SHARES = [0.40, 0.50, 0.60]      # customer pays 40%, 50% or 60% of the balance
COLLECTIONS_RECOVERY = [0.15, 0.25, 0.35]   # what normal collections would recover
SETUP_COST = 0.01                           # paid on acceptance
COMPLETION_COST = 0.02                      # paid on completion
FAILURE_COST = 0.02                         # extra collections work if it fails
FAILED_RECOVERY_FACTOR = 0.8                # a failed settlement recovers less than collections would have (time lost)


def breakeven_completion(share, recovery, setup=SETUP_COST, completion_cost=COMPLETION_COST,
                         failure_cost=FAILURE_COST, failed_factor=FAILED_RECOVERY_FACTOR):
    """Share of ACCEPTED settlements that must complete for the offer to beat collections.
    Returns None if the offer can't win even when every settlement completes."""
    failed_net = recovery * failed_factor - failure_cost
    completed_net = share - completion_cost
    gap_needed = recovery + setup - failed_net
    gain_per_completion = completed_net - failed_net
    if gain_per_completion <= 0:
        return None
    breakeven = gap_needed / gain_per_completion
    return breakeven if breakeven <= 1 else None


def scenarios(**costs):
    rows = []
    for share in SETTLEMENT_SHARES:
        for recovery in COLLECTIONS_RECOVERY:
            b = breakeven_completion(share, recovery, **costs)
            rows.append({
                "settlement_share": share,
                "collections_recovery": recovery,
                "breakeven_completion_rate": None if b is None else round(b, 3),
                "reading": "never worth it" if b is None else f"worth it if more than {b:.0%} complete",
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    table = scenarios()
    table.to_csv(OUT / "settlement_breakeven.csv", index=False)
    print("Costs split by timing: 1% setup, 2% on completion, 2% extra if it fails\n")
    print(table.to_string(index=False))

    # For comparison, my earlier simpler model: one 3% cost, charged only on completion.
    # A completed settlement costs 3% in both models. The difference is that the
    # split model also charges 3% (setup plus extra collections) when one fails.
    simple = scenarios(setup=0.0, completion_cost=0.03, failure_cost=0.0)
    simple.to_csv(OUT / "settlement_breakeven_simple_costs.csv", index=False)
    print("\nFor comparison, a single 3% cost charged only on completion:\n")
    print(simple.to_string(index=False))
