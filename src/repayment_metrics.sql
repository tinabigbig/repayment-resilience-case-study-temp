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
-- Only compare a month with the month straight after it. If a snapshot is
-- missing, LEAD() would pair months two apart, so those pairs are dropped here
-- and counted separately (see the gap check at the bottom).
, consecutive AS (
  SELECT *
  FROM paired
  WHERE next_month IS NULL
     OR next_month = observation_month + INTERVAL '1' MONTH
)
SELECT observation_month, dpd_bucket,
       COUNT(*) AS accounts,
       SUM(outstanding_balance) AS exposure_cad,
       AVG(CASE WHEN next_month IS NOT NULL AND days_past_due > 0 AND next_dpd = 0
                THEN 1.0 WHEN next_month IS NOT NULL AND days_past_due > 0 THEN 0.0 END) AS next_period_cure_rate,
       AVG(CASE WHEN next_month IS NOT NULL AND days_past_due BETWEEN 1 AND 30 AND next_dpd >= 60
                THEN 1.0 WHEN next_month IS NOT NULL AND days_past_due BETWEEN 1 AND 30 THEN 0.0 END) AS next_period_roll_to_60plus
FROM consecutive
GROUP BY observation_month, dpd_bucket
ORDER BY observation_month, dpd_bucket;
-- Production work: verify monthly continuity, closure/charge-off censoring,
-- stable loan identifiers, idempotency, missing snapshots and treatment assignment.

-- Gap check (run this on its own first). It counts account-months whose next
-- snapshot is not exactly one month later. If it isn't close to zero, fix the
-- snapshots before trusting the cure and roll rates above.
WITH ordered AS (
  SELECT account_id, observation_month,
         LEAD(observation_month) OVER (PARTITION BY account_id ORDER BY observation_month) AS next_month
  FROM loan_monthly_snapshot
)
SELECT COUNT(*) AS non_consecutive_pairs
FROM ordered
WHERE next_month IS NOT NULL
  AND next_month <> observation_month + INTERVAL '1' MONTH;
