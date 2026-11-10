# Repayment Resilience

A product case study on helping borrowers who fall behind on a credit product get back on track.

I put this together in November 2026 while applying for a repayments and recovery product role. It's my own work. The data is simulated, and nothing here comes from a lender or from any employer.

## The idea

A lot of missed payments aren't about ability to pay. The due date simply lands a few days before payday, the debit fails, a fee follows, and the account starts to slide. So the first question I wanted to test was:

> If eligible customers can move their due date to line up with payday, do more of them pay on time, without causing harm somewhere else?

The second piece is for people who genuinely can't afford their current payments. They need a person to look at their situation, not an automated retry.

## What's in the repo

| Path | What it is |
| --- | --- |
| `docs/one_page_product_case.pdf` | One-page summary of the case |
| `docs/PRD_and_experiment.md` | The fuller write-up: requirements, test design, hardship and settlement ideas, risks |
| `src/analysis.py` | Builds the simulated loan book, runs the test analysis and the portfolio views |
| `src/power_analysis.py` | Sample size needed for the test |
| `src/repayment_metrics.sql` | A SQL template for cure and roll rates from monthly account snapshots |
| `data/` and `outputs/` | The simulated data and the results tables |

To reproduce everything (Python 3.10+):

```bash
pip install -r requirements.txt
python src/analysis.py
python src/power_analysis.py
```

## The test

- **Who's in it:** customers whose due date is more than 4 days from payday, no more than 30 days behind, and not flagged for hardship.
- **How:** randomize by customer, half keep their current due date and half get the option to align it. I analyze everyone as assigned (intention to treat), whether or not they took the option.
- **Main measure:** did they make the next scheduled payment on time?
- **What would make me stop:** more complaints, NSF fees, missed payments later on, accounts rolling further behind, or worse outcomes for vulnerable customers.

## How big the test needs to be

This was the most useful part to work out. With a 72% on-time baseline, 5% significance and 80% power:

| Smallest lift worth detecting | Customers per group | Total |
| --- | ---: | ---: |
| 2 points | 7,733 | 15,466 |
| 3 points | 3,395 | 6,790 |
| 5 points | 1,191 | 2,382 |

My simulated test has 3,408 customers in total, so it couldn't reliably detect a 3-point lift. In a real setting, the first thing to check is how many eligible customers come through each month, because that decides how long the test has to run.

## What the simulation shows

Aligned due dates: 80.6% paid on time. Control: 72.0%. That's 8.6 points (95% CI 5.8 to 11.5).

To be clear about what this means: I built a 7.5-point effect into the simulated data, so this result only shows the analysis picks it up. Whether due-date alignment works for real borrowers is exactly what a live test would answer.

## Hardship and settlement

Phase 1 doesn't create any new credit. People reporting hardship go to a person who checks affordability and can offer a temporary lower payment, a new due date or a structured plan.

Phase 2 is where hardship and settlement loans come in. My rule for settlements is simple: offer one only if the expected net recovery from the settlement beats what normal collections would recover, after costs, and only if the customer can actually afford it. The PRD has the details and who would need to sign off.

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
