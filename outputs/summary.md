# Results on simulated data

## Bottom line

Don't roll it out yet. Customers paid on time more often against their own due date,
but that didn't turn into clearly more money collected by day 60. I'd keep testing.

## What I tested

6,000 simulated accounts. 3,408 were eligible and split at random:
1,725 could move their due date to payday, 1,683 kept their current date.

"95% CI" below is the range the true difference most likely falls in.
If that range includes zero, the result isn't clear.

## On time against their own due date

- Aligned 80.6% vs control 72.0%, a difference of +8.6 points (95% CI 5.8 to 11.5).
- I built a 7.5-point lift into the simulation, so this only shows the analysis picks it up.

## Money in hand on a fixed calendar (the measure that decides)

- First payment collected by day 30: -1.4 points (95% CI -4.3 to 1.4).
- First payment collected by day 60: +1.6 points (95% CI -0.3 to 3.5).
- Dollars collected per customer by day 60: +6.72 CAD (95% CI -0.33 to 13.77).
- Both day-60 ranges include zero, so there's no clear gain in collections.

## How big a real test would need to be

Planned on day-60 collection (90.4% baseline, 5% significance, 80% power):
3,085 customers per group to detect a 2-point lift, 1,293 for 3 points, 404 for 5.
This demo has about 1,700 per group, enough for 3 points but not 2.

## Hardship

179 accounts would go to a person for an affordability review. Nobody is auto-approved.

## What this can't tell you

There's no charge-off or recovery data here, so I don't estimate savings.
