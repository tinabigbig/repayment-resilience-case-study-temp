# Repayment Resilience

A product case study on helping borrowers who fall behind on a credit product get back on track.

I put this together in November 2026 while applying for a repayments and recovery product role. It's my own work. The data is simulated, and nothing here comes from a lender or from any employer.

## The idea

Some missed payments may not be about ability to pay at all. If the due date lands a few days before payday, the debit can fail, a fee follows, and the account starts to slide. I don't know how common that is, which is why I'd test it rather than assume it. The first question:

> If eligible customers can move their due date to line up with payday, do more of them pay on time, without causing harm somewhere else?

The second piece is for people who genuinely can't afford their current payments. They need a person to look at their situation, not an automated retry.

## What's in the repo

| Path | What it is |
| --- | --- |
| `docs/one_page_product_case.pdf` | One-page summary of the case |
| `docs/PRD_and_experiment.md` | The fuller write-up: requirements, test design, hardship and settlement ideas, risks |
| `src/analysis.py` | Builds the simulated loan book, runs the test analysis and the portfolio views |
| `src/power_analysis.py` | Sample size, for the decision measure and for on-time |
| `src/settlement_breakeven.py` | When a settlement beats normal collections |
| `src/repayment_metrics.sql` | A SQL template for cure and roll rates from monthly account snapshots |
| `tests/test_project.py` | Checks: one row per customer, only eligible customers randomized, sensible rates, and the README's numbers |
| `data/` and `outputs/` | The simulated data and the results tables |

To reproduce everything (Python 3.10+):

```bash
pip install -r requirements.txt
python src/analysis.py
python src/power_analysis.py
python src/settlement_breakeven.py
python -m pytest -q        # checks on the data, the sample-size and break-even maths, and the headline results
```

## The test

The test would include customers whose due date is more than 4 days from payday, who are no more than 30 days behind, and who haven't reported hardship. I'd randomize by customer: half keep their current due date, half get the option to move it to payday. Everyone is analyzed in the group they were assigned to, whether or not they took the option.

The number that decides it is whether the first payment was collected by day 60 after assignment, and how many dollars came in by then. I use a fixed calendar on purpose. Moving a due date also moves the finish line for "on time", so on-time alone could show a lift that's really just a later deadline. On-time against the customer's own due date and collection by day 30 are still tracked, just not used to decide.

I'd stop the test if complaints, NSF fees, later missed payments or accounts rolling further behind went up, or if vulnerable customers did worse.

## How big the test needs to be

I plan the test on the decision measure, not on on-time. The two give very different answers because their baselines differ (5% significance, 80% power):

| Smallest lift worth detecting | Day-60 collection, 90.4% baseline: per group | On time, 72% baseline: per group |
| --- | ---: | ---: |
| 2 points | 3,085 | 7,733 |
| 3 points | 1,293 | 3,395 |
| 5 points | 404 | 1,191 |

My simulated test has 3,408 customers in total (about 1,700 per group). That's enough to detect a 3-point change in day-60 collection, but not a 2-point one, and the simulated day-60 difference was only 1.6 points. In a real setting, the first thing to check is how many eligible customers come through each month, because that decides how long the test has to run. Repeated looks at the data, drop-outs and customers who share accounts would all push these numbers up.

## What the simulation shows

"95% CI" is the range the true difference most likely falls in. If it includes zero, the result isn't clear.

| Measure | Aligned | Control | Difference (95% CI) |
| --- | ---: | ---: | --- |
| On time vs own due date | 80.6% | 72.0% | +8.6 pts (5.8 to 11.5) |
| First payment collected by day 30 | 76.5% | 78.0% | -1.4 pts (-4.3 to 1.4) |
| First payment collected by day 60 (decision measure) | 92.0% | 90.4% | +1.6 pts (-0.3 to 3.5) |
| Dollars collected per customer by day 60 | $135.0 | $128.3 | +$6.7 (-$0.3 to $13.8) |

I built a 7.5-point effect into "on time" in the simulated data, so the first row only shows the analysis picks it up. The rows below it are the useful lesson: the on-time improvement does not turn into a statistically clear improvement in collections by day 60. In this simulation the due-date shift and the payment outcome both change at once, so I can't say how much of the gap comes from later deadlines. What it does show is why a repayment test should be judged on a fixed calendar rather than only on performance against each customer's own due date. On these results I wouldn't roll it out; I'd keep testing.

## Hardship and settlement

Phase 1 doesn't create any new credit. People reporting hardship go to a person who checks affordability and can offer a temporary lower payment, a new due date or a structured plan.

Phase 2 is where hardship and settlement loans come in. My rule for settlements is simple: offer one only if the expected net recovery from the settlement beats what normal collections would recover, after costs, and only if the customer can actually afford it.

The catch is that an accepted settlement only helps if it's completed. Three numbers get mixed up easily, so I keep them apart: the acceptance rate (accepted out of offers made), the completion rate (completed out of those accepted) and the overall recovery from everyone offered. `settlement_breakeven.py` works out the completion rate, among customers who accept, that the offer needs to come out ahead.

Costs don't all land at the same time, so I split them: a setup cost as soon as someone accepts (1% of the balance), a cost when the settlement completes (2%), and extra collections work when it falls through (2%). A failed settlement also recovers 80% of what collections would have. All of these are assumptions:

| Customer pays | Collections would recover 15% | 25% | 35% |
| --- | ---: | ---: | ---: |
| 40% of balance | 21% must complete | 40% | 83% |
| 50% of balance | 16% | 27% | 45% |
| 60% of balance | 13% | 20% | 31% |

Reading one cell: if collections would get back 25% and the settlement asks for 50%, the offer pays off once more than about 1 in 4 accepted settlements are completed. If I charge all the cost only on completion, as a simpler model would, that bar drops to about 19%. The difference is the cost of settlements that are accepted and then fail, which is easy to forget and makes offers look better than they are. The deeper the discount and the better normal collections perform, the higher the bar.

One more caution: customers who accept may be the ones who would have paid anyway, so the real test is the overall recovery from everyone offered, compared with a group not offered a settlement, not just the outcome for those who accept. The PRD has who would need to sign off.

## On-load collections

Taking part of a payment when money is loaded to the account can raise recoveries, but it can also leave someone short for rent or groceries. If tested, it should be opt-in, capped, have exemptions, and be judged on complaints and hardship as much as on dollars recovered.

## Measuring the money

Without real charge-off data I don't put a dollar figure on this. With real data, the way I'd frame it is losses avoided:

`(control charge-off roll rate - treatment charge-off roll rate) x balance at risk x loss rate at charge-off`

That's a starting point to agree with Finance and Credit Risk, not a profit number.

## Canadian rules to check

Who the legal lender is and which rules apply; cost-of-borrowing disclosure; the criminal interest rate limit and how it's calculated; consent for any change to terms; accurate credit bureau reporting; privacy; and fair treatment of people in hardship. Any real version would need legal review first. This isn't legal advice.

## References

- [Criminal Code interest rate amendments (Canada Gazette, 2025)](https://gazette.gc.ca/rp-pr/p2/2025/2025-01-01/html/si-tr4-eng.html)
- [FCAC: personal loans and cost of borrowing](https://www.canada.ca/en/financial-consumer-agency/services/rights-responsibilities/rights-credit-loans/rights-personal-loans.html)
- [FCAC: fixing errors on your credit report](https://www.canada.ca/en/financial-consumer-agency/services/credit-reports-score/check-errors.html)

Tina Liang
