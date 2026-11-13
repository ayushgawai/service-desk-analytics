-- Client health: SLA attainment + volume + uptime per account (whole period).
with t as (select account_id, count(*) tickets,
    1.0 - avg(case when is_breached then 1.0 else 0.0 end) sla_attainment,
    median(first_response_minutes) median_frt_min from {{ ref('fct_tickets') }} group by 1),
u as (select account_id, avg(uptime_pct) avg_uptime_pct from {{ ref('stg_uptime_checks') }} group by 1)
select t.*, u.avg_uptime_pct,
  case when t.sla_attainment >= .95 and u.avg_uptime_pct >= 99.5 then 'healthy'
       when t.sla_attainment >= .85 then 'watch' else 'at_risk' end as health_band
from t join u using (account_id)
