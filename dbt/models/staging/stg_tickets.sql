-- Canonical SLA logic lives here; see docs/kpis.md. Breach = resolution
-- time strictly greater than the policy target for the ticket priority.
select t.*,
  t.resolution_hours > p.sla_resolution_hours as is_breached,
  t.first_response_minutes > p.sla_first_response_minutes as is_frt_breached
from {{ source('raw','raw_tickets') }} t
join {{ ref('stg_sla_policies') }} p using (priority)
