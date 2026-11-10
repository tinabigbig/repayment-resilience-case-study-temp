"""
Basic tests. Run from the project root:  python -m pytest -q
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from power_analysis import required_per_arm          # noqa: E402
from settlement_breakeven import breakeven_completion  # noqa: E402


@pytest.fixture(scope="module")
def accounts():
    subprocess.run([sys.executable, str(ROOT / "src" / "analysis.py")], check=True, capture_output=True)
    return pd.read_csv(ROOT / "data" / "synthetic_accounts.csv")


def test_one_row_per_customer(accounts):
    assert accounts["customer_id"].is_unique


def test_only_eligible_customers_are_randomized(accounts):
    in_test = accounts["variant"].isin(["control", "aligned"])
    assert (in_test == accounts["eligible_for_experiment"]).all()


def test_groups_are_roughly_balanced(accounts):
    sizes = accounts.loc[accounts["variant"] != "not_eligible", "variant"].value_counts()
    assert abs(sizes["aligned"] - sizes["control"]) / sizes.sum() < 0.05


def test_rates_are_between_0_and_1(accounts):
    for col in ["next_payment_success", "collected_by_day30", "collected_by_day60"]:
        assert accounts[col].between(0, 1).all()


def test_day60_never_below_day30(accounts):
    assert (accounts["collected_by_day60"] >= accounts["collected_by_day30"]).all()


def test_amount_collected_never_exceeds_payment(accounts):
    assert (accounts["amount_collected_by_day60_cad"] <= accounts["monthly_payment_cad"] + 0.01).all()


def test_sample_size_matches_readme():
    assert required_per_arm(0.72, 0.02) == 7733
    assert required_per_arm(0.72, 0.03) == 3395
    assert required_per_arm(0.72, 0.05) == 1191


def test_bigger_lift_needs_fewer_customers():
    assert required_per_arm(0.72, 0.05) < required_per_arm(0.72, 0.03) < required_per_arm(0.72, 0.02)


def test_breakeven_example_from_readme():
    # costs split by timing
    assert breakeven_completion(0.50, 0.25) == pytest.approx(0.267, abs=0.001)
    # all cost charged only on completion gives the lower, simpler figure
    assert breakeven_completion(0.50, 0.25, setup=0.0, completion_cost=0.03, failure_cost=0.0) == pytest.approx(0.185, abs=0.001)


def test_failed_settlement_costs_raise_the_bar():
    split = breakeven_completion(0.50, 0.25)
    simple = breakeven_completion(0.50, 0.25, setup=0.0, completion_cost=0.03, failure_cost=0.0)
    assert split > simple


def test_breakeven_rises_when_collections_do_better():
    assert breakeven_completion(0.50, 0.15) < breakeven_completion(0.50, 0.25) < breakeven_completion(0.50, 0.35)


def test_settlement_never_wins_if_it_pays_less_than_collections():
    assert breakeven_completion(0.20, 0.25) is None


def test_sample_size_for_decision_measure():
    assert required_per_arm(0.9037, 0.02) == 3085
    assert required_per_arm(0.9037, 0.03) == 1293
    assert required_per_arm(0.9037, 0.05) == 404


def test_headline_results_match_readme(accounts):
    windows = pd.read_csv(ROOT / "outputs" / "fixed_window_results.csv").set_index("measure")
    assert windows.loc["on time vs own due date", "difference"] == pytest.approx(8.62, abs=0.01)
    assert windows.loc["first payment collected by day 30", "difference"] == pytest.approx(-1.43, abs=0.01)
    assert windows.loc["first payment collected by day 60", "difference"] == pytest.approx(1.63, abs=0.01)
    assert windows.loc["CAD collected per customer by day 60", "difference"] == pytest.approx(6.72, abs=0.01)
    # day-60 confidence interval includes zero, as the README says
    row = windows.loc["first payment collected by day 60"]
    assert row["ci_low"] < 0 < row["ci_high"]


def test_breakeven_when_completed_settlement_equals_collections():
    # if a completed settlement nets exactly what collections would, it never wins
    assert breakeven_completion(0.27, 0.25, setup=0.0, completion_cost=0.02, failure_cost=0.0, failed_factor=1.0) is None
