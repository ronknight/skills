-- Last-touch attribution within a window. DuckDB / PostgreSQL syntax.
-- Inputs (build these from the raw extracts first):
--   orders(order_ref, person_id, order_date, amount)              billed orders only
--   engagement(person_id, campaign_id, signal, event_time)        signal in ('click', 'open')
--   person_fanout(person_id, fan_out_factor)                      1 / number of accounts per email
-- Windows are parameters: 30-day click (tier A), 14-day open (tier B).

WITH candidates AS (
    SELECT
        o.order_ref,
        o.person_id,
        o.order_date,
        o.amount,
        e.campaign_id,
        e.signal,
        e.event_time,
        CASE WHEN e.signal = 'click' THEN 'A' ELSE 'B' END AS tier,
        ROW_NUMBER() OVER (
            PARTITION BY o.order_ref
            ORDER BY
                CASE WHEN e.signal = 'click' THEN 0 ELSE 1 END,   -- any qualifying click beats any open
                e.event_time DESC                                  -- then the most recent
        ) AS rn
    FROM orders o
    JOIN engagement e
      ON e.person_id = o.person_id
     AND e.event_time <= o.order_date
     AND (
            (e.signal = 'click' AND e.event_time >= o.order_date - INTERVAL 30 DAY)
         OR (e.signal = 'open'  AND e.event_time >= o.order_date - INTERVAL 14 DAY)
     )
)
SELECT
    c.order_ref,
    c.campaign_id,
    c.person_id,
    c.tier,
    c.signal,
    CAST(c.order_date AS DATE) - CAST(c.event_time AS DATE) AS lag_days,
    c.amount * COALESCE(f.fan_out_factor, 1.0)              AS attributed_amount,
    COALESCE(f.fan_out_factor, 1.0)                         AS fan_out_factor
FROM candidates c
LEFT JOIN person_fanout f USING (person_id)
WHERE c.rn = 1;

-- Orders with no row above are unattributed. Count them; don't drop them.
-- PostgreSQL: write the intervals as INTERVAL '30 days' and INTERVAL '14 days'.
-- Leaderboard: sum attributed_amount by campaign_id and tier, divide tier A by
-- delivered recipients for revenue per recipient. Keep tier A and tier B in
-- separate columns.
