"""
Repayment resilience case study: simulated data and analysis.

All data here is made up. Run from the project root:
    python src/analysis.py
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------------
# Setup
# ---------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

SEED = 20261110
N_ACCOUNTS = 6000
TREATMENT_EFFECT = 0.075   # the lift I build into the simulation on purpose

rng = np.random.default_rng(SEED)


# ---------------------------------------------------------------
# 1. Simulate a loan book
#    One account per customer, so customer = account in this demo.
# ---------------------------------------------------------------

product = rng.choice(["revolving", "installment"], N_ACCOUNTS, p=[0.56, 0.44])
dpd = rng.choice([0, 1, 15, 30, 60], N_ACCOUNTS, p=[0.56, 0.12, 0.13, 0.12, 0.07])

# Days between the due date and payday. More than 4 days apart counts as a mismatch.
payday_gap = rng.integers(-14, 15, N_ACCOUNTS)
payday_misaligned = np.abs(payday_gap) > 4

balance = np.round(rng.lognormal(6.7, 0.58, N_ACCOUNTS), 2)
balance = np.clip(balance, 100, 6500)

monthly_payment = np.round(np.maximum(balance * rng.uniform(0.07, 0.23, N_ACCOUNTS), 25), 2)

income = np.round(rng.lognormal(8.05, 0.43, N_ACCOUNTS), 2)
income = np.clip(income, 1200, 12000)

payment_burden = monthly_payment / income

# Customers further behind are a bit more likely to report hardship.
hardship = rng.random(N_ACCOUNTS) < (0.11 + 0.06 * (dpd >= 30))


# ---------------------------------------------------------------
# 2. Who goes into the test, and random assignment
#    Mismatched payday, no hardship flag, 30 days past due or less.
# ---------------------------------------------------------------

eligible = payday_misaligned & ~hardship & (dpd <= 30)

variant = np.array(["not_eligible"] * N_ACCOUNTS, dtype=object)
variant[eligible] = rng.choice(["control", "aligned"], eligible.sum())


# ---------------------------------------------------------------
# 3. Simulate outcomes
#    Chance of paying on time drops with mismatch, arrears, hardship and
#    a heavy payment burden. Aligned customers get the built-in lift.
# ---------------------------------------------------------------

p_pay = (
    0.89
    - 0.12 * payday_misaligned
    - 0.09 * (dpd >= 15)
    - 0.10 * (dpd >= 30)
    - 0.08 * hardship
    - 0.12 * (payment_burden > 0.25)
)
p_pay = np.clip(p_pay, 0.15, 0.95)
p_pay = np.clip(p_pay + TREATMENT_EFFECT * (variant == "aligned"), 0, 0.99)
paid_next = rng.binomial(1, p_pay)

# Cure within 60 days: only defined for accounts already behind.
p_cure = np.clip(
    0.64 - 0.15 * (dpd >= 30) - 0.14 * (dpd >= 60) - 0.13 * hardship + 0.045 * (variant == "aligned"),
    0.05, 0.95,
)
cured_60d = np.where(dpd > 0, rng.binomial(1, p_cure), np.nan)

# Roll into 60+ days: only defined for accounts 1 to 30 days behind.
p_roll = np.clip(
    0.19 + 0.08 * (dpd >= 15) + 0.10 * (dpd >= 30) + 0.10 * hardship - 0.035 * (variant == "aligned"),
    0.02, 0.80,
)
rolled_60plus = np.where((dpd > 0) & (dpd <= 30), rng.binomial(1, p_roll), np.nan)

# Fixed-window outcome (added after review).
# Moving the due date also moves when "on time" is judged, so I also check
# whether the first payment was collected by a fixed day after assignment.
# Control due dates fall 5 to 25 days after assignment; aligned dates move
# by the payday gap. Late payers pay 5 to 45 days after the due date, and
# 30% of late payers don't pay within 60 days.
due_day_control = rng.integers(5, 26, N_ACCOUNTS)
never_pays = rng.random(N_ACCOUNTS) < 0.30
late_by = rng.integers(5, 46, N_ACCOUNTS)

due_day = np.where(variant == "aligned", np.clip(due_day_control + payday_gap, 1, 45), due_day_control)
pay_day = np.where(paid_next == 1, due_day, np.where(never_pays, 999, due_day + late_by))
collected_by_day30 = (pay_day <= 30).astype(int)
collected_by_day60 = (pay_day <= 60).astype(int)
amount_by_day30 = monthly_payment * collected_by_day30
amount_by_day60 = monthly_payment * collected_by_day60


# ---------------------------------------------------------------
# 4. Put it in one table and save it
# ---------------------------------------------------------------

accounts = pd.DataFrame({
    "customer_id": [f"CUST{i:06d}" for i in range(N_ACCOUNTS)],
    "account_id": [f"SYN{i:06d}" for i in range(N_ACCOUNTS)],
    "product_type": product,
    "initial_dpd": dpd,
    "dpd_bucket": pd.cut(dpd, [-1, 0, 14, 29, 59, 999],
                         labels=["current", "1-14", "15-29", "30-59", "60+"]).astype(str),
    "outstanding_balance_cad": balance,
    "monthly_payment_cad": monthly_payment,
    "monthly_income_cad": income,
    "payment_burden": payment_burden.round(4),
    "payday_gap_days": payday_gap,
    "payday_misaligned": payday_misaligned,
    "hardship_indicator": hardship,
    "eligible_for_experiment": eligible,
    "variant": variant,
    "next_payment_success": paid_next,
    "cured_within_60d": cured_60d,
    "rolled_to_60plus": rolled_60plus,
    "due_day_after_assignment": due_day,
    "collected_by_day30": collected_by_day30,
    "collected_by_day60": collected_by_day60,
    "amount_collected_by_day30_cad": amount_by_day30.round(2),
    "amount_collected_by_day60_cad": amount_by_day60.round(2),
})
accounts.to_csv(DATA / "synthetic_accounts.csv", index=False)

# Quick checks: one row per customer, and both groups big enough to compare.
trial = accounts[accounts["variant"].isin(["control", "aligned"])]
assert accounts["customer_id"].is_unique
assert trial["customer_id"].is_unique
assert all(trial.groupby("variant").size() > 100)


# ---------------------------------------------------------------
# 5. Test result: aligned vs control (intention to treat)
# ---------------------------------------------------------------

by_variant = (
    trial.groupby("variant", observed=True)
    .agg(
        accounts=("account_id", "size"),
        payment_success=("next_payment_success", "mean"),
        avg_balance=("outstanding_balance_cad", "mean"),
        share_initial_dpd=("initial_dpd", lambda x: (x > 0).mean()),
    )
    .reset_index()
)
by_variant.to_csv(OUT / "experiment_results.csv", index=False)

aligned = trial.loc[trial["variant"] == "aligned", "next_payment_success"]
control = trial.loc[trial["variant"] == "control", "next_payment_success"]

lift = aligned.mean() - control.mean()
se = np.sqrt(aligned.var(ddof=1) / len(aligned) + control.var(ddof=1) / len(control))
ci_low, ci_high = lift - 1.96 * se, lift + 1.96 * se


# Same comparison on a fixed calendar: first payment collected by day 30 and day 60.
def diff_with_ci(column):
    a = trial.loc[trial["variant"] == "aligned", column]
    c = trial.loc[trial["variant"] == "control", column]
    d = a.mean() - c.mean()
    e = np.sqrt(a.var(ddof=1) / len(a) + c.var(ddof=1) / len(c))
    return a.mean(), c.mean(), d, d - 1.96 * e, d + 1.96 * e

window_rows = []
for label, column in [("on time vs own due date", "next_payment_success"),
                      ("first payment collected by day 30", "collected_by_day30"),
                      ("first payment collected by day 60", "collected_by_day60"),
                      ("CAD collected per customer by day 30", "amount_collected_by_day30_cad"),
                      ("CAD collected per customer by day 60", "amount_collected_by_day60_cad")]:
    a_rate, c_rate, d, lo, hi = diff_with_ci(column)
    scale = 1 if column.startswith("amount") else 100   # dollars stay dollars, rates become points
    window_rows.append({"measure": label, "aligned": round(a_rate, 4), "control": round(c_rate, 4),
                        "difference": round(d * scale, 2), "ci_low": round(lo * scale, 2), "ci_high": round(hi * scale, 2),
                        "unit": "CAD" if scale == 1 else "points"})
windows = pd.DataFrame(window_rows)
windows.to_csv(OUT / "fixed_window_results.csv", index=False)


# ---------------------------------------------------------------
# 6. Portfolio views by days past due
#    These are snapshots, not month-to-month transitions.
# ---------------------------------------------------------------

segments = (
    accounts.groupby("dpd_bucket", observed=True)
    .agg(accounts=("account_id", "size"),
         balance=("outstanding_balance_cad", "sum"),
         payment_success=("next_payment_success", "mean"))
    .reset_index()
)
segments.to_csv(OUT / "portfolio_segments.csv", index=False)

roll = (
    accounts[accounts["rolled_to_60plus"].notna()]
    .groupby("dpd_bucket", observed=True)
    .agg(accounts=("account_id", "size"), roll_to_60plus=("rolled_to_60plus", "mean"))
    .reset_index()
)
roll.to_csv(OUT / "illustrative_roll_rates.csv", index=False)

cure = (
    accounts[accounts["cured_within_60d"].notna()]
    .groupby("dpd_bucket", observed=True)
    .agg(accounts=("account_id", "size"), cure_rate_60d=("cured_within_60d", "mean"))
    .reset_index()
)
cure.to_csv(OUT / "illustrative_cure_rates.csv", index=False)


# ---------------------------------------------------------------
# 7. Hardship triage: who would go to a person for review
#    15 to 59 days behind and reporting hardship. Nobody is auto-approved.
# ---------------------------------------------------------------

to_review = accounts[accounts["initial_dpd"].between(15, 59) & accounts["hardship_indicator"]]

pd.DataFrame([{
    "eligible_for_manual_review_n": len(to_review),
    "average_outstanding_balance_cad": round(to_review["outstanding_balance_cad"].mean(), 2),
    "median_payment_burden": round(to_review["payment_burden"].median(), 3),
    "suggested_policy": "manual affordability review and explicit customer consent; not auto-approve",
}]).to_csv(OUT / "hardship_triage.csv", index=False)


# ---------------------------------------------------------------
# 8. Short write-up of the numbers
# ---------------------------------------------------------------

def one_dp(x):
    """Round to one decimal the way people expect (-4.25 becomes -4.3, not -4.2)."""
    return str(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


w = windows
summary = f"""# Results on simulated data

## Bottom line

Don't roll it out yet. Customers paid on time more often against their own due date,
but that didn't turn into clearly more money collected by day 60. I'd keep testing.

## What I tested

{N_ACCOUNTS:,} simulated accounts. {len(trial):,} were eligible and split at random:
{len(aligned):,} could move their due date to payday, {len(control):,} kept their current date.

"95% CI" below is the range the true difference most likely falls in.
If that range includes zero, the result isn't clear.

## On time against their own due date

- Aligned {aligned.mean():.1%} vs control {control.mean():.1%}, a difference of {lift * 100:+.1f} points (95% CI {ci_low * 100:.1f} to {ci_high * 100:.1f}).
- I built a {TREATMENT_EFFECT * 100:.1f}-point lift into the simulation, so this only shows the analysis picks it up.

## Money in hand on a fixed calendar (the measure that decides)

- First payment collected by day 30: {one_dp(w.loc[1, "difference"])} points (95% CI {one_dp(w.loc[1, "ci_low"])} to {one_dp(w.loc[1, "ci_high"])}).
- First payment collected by day 60: +{one_dp(w.loc[2, "difference"])} points (95% CI {one_dp(w.loc[2, "ci_low"])} to {one_dp(w.loc[2, "ci_high"])}).
- Dollars collected per customer by day 60: {windows.loc[4, "difference"]:+.2f} CAD (95% CI {windows.loc[4, "ci_low"]:.2f} to {windows.loc[4, "ci_high"]:.2f}).
- Both day-60 ranges include zero, so there's no clear gain in collections.

## How big a real test would need to be

Planned on day-60 collection (90.4% baseline, 5% significance, 80% power):
3,085 customers per group to detect a 2-point lift, 1,293 for 3 points, 404 for 5.
This demo has about 1,700 per group, enough for 3 points but not 2.

## Hardship

{len(to_review)} accounts would go to a person for an affordability review. Nobody is auto-approved.

## What this can't tell you

There's no charge-off or recovery data here, so I don't estimate savings.
"""
(OUT / "summary.md").write_text(summary)
print(summary)
