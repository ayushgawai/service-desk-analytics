-- One row per account per created-date. Backlog = tickets created that day
-- still unresolved at end of day (approximation documented in kpis.md).
select t.account_id, cast(t.created_at as date) as day,
  count(*) as tickets_created,
  sum(case when t.is_breached then 1 else 0 end) as tickets_breached,
  1.0 - avg(case when t.is_breached then 1.0 else 0.0 end) as sla_attainment,
  median(t.first_response_minutes) as median_first_response_minutes,
  median(t.resolution_hours) as median_resolution_hours,
  sum(case when cast(t.resolved_at as date) > cast(t.created_at as date) then 1 else 0 end) as backlog_eod
from {{ ref('fct_tickets') }} t group by 1, 2
