-- ANSI-style SQL outline. Replace with real warehouse schema and tested dialect.
-- Assumes one monthly observation per account, with as-of-period snapshot.
-- Do not compare stock delinquency buckets to transition rates without a stable cohort.
WITH monthly AS (
  SELECT account_id, observation_month, days_past_due, outstanding_balance,
         CASE WHEN days_past_due = 0 THEN 'current'
              WHEN days_past_due BETWEEN 1 AND 14 THEN '1-14'
              WHEN days_past_due BETWEEN 15 AND 29 THEN '15-29'
              WHEN days_past_due BETWEEN 30 AND 59 THEN '30-59'
              ELSE '60+' END AS dpd_bucket
  FROM loan_monthly_snapshot
), paired AS (
  SELECT account_id, observation_month, days_past_due, outstanding_balance, dpd_bucket,
         LEAD(days_past_due) OVER (PARTITION BY account_id ORDER BY observation_month) AS next_dpd,
         LEAD(observation_month) OVER (PARTITION BY account_id ORDER BY observation_month) AS next_month
  FROM monthly
)
SELECT observation_month, dpd_bucket,
       COUNT(*) AS accounts,
       SUM(outstanding_balance) AS exposure_cad,
       AVG(CASE WHEN next_month IS NOT NULL AND days_past_due > 0 AND next_dpd = 0
                THEN 1.0 WHEN next_month IS NOT NULL AND days_past_due > 0 THEN 0.0 END) AS next_period_cure_rate,
       AVG(CASE WHEN next_month IS NOT NULL AND days_past_due BETWEEN 1 AND 30 AND next_dpd >= 60
                THEN 1.0 WHEN next_month IS NOT NULL AND days_past_due BETWEEN 1 AND 30 THEN 0.0 END) AS next_period_roll_to_60plus
FROM paired
GROUP BY observation_month, dpd_bucket
ORDER BY observation_month, dpd_bucket;
-- Production work: verify monthly continuity, closure/charge-off censoring,
-- stable loan identifiers, idempotency, missing snapshots and treatment assignment.
