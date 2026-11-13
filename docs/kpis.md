# KPI definitions (single source of truth — dashboard, dbt and reports must match)

| KPI | Definition | Source |
|---|---|---|
| SLA breach | `resolution_hours > sla_resolution_hours` for the ticket priority (P1 4h, P2 8h, P3 24h, P4 72h). Strictly greater; exactly-at-target is not a breach. | `stg_tickets.is_breached` |
| SLA attainment | `1 − breached / tickets` over tickets *created* in the period (not resolved in it). | `agg_account_day.sla_attainment` |
| First-response time (FRT) | Minutes creation → first agent reply; reported as median, target P1 15 / P2 30 / P3 120 / P4 480 min. | `agg_account_day.median_first_response_minutes` |
| Backlog (EOD) | Tickets created that day whose `resolved_at` date is after the created date. Approximation of open-at-midnight; a true snapshot needs hourly state history (see Limitations). | `agg_account_day.backlog_eod` |
| Uptime % | Mean of daily synthetic probe aggregates per account. | `agg_client_health.avg_uptime_pct` |
| Health band | `healthy`: attainment ≥ .95 and uptime ≥ 99.5 · `watch`: attainment ≥ .85 · else `at_risk`. | `agg_client_health.health_band` |
| Breach prediction | P(breach) at creation from priority/category/channel/complexity/tier/seats/hour/dow only — no post-creation fields. Time-based 80/20 holdout. | `src/predict.py` |
| Staffing A/B effect | Post-day-120 mean per-account breach rate, treatment − control; 95% CI by bootstrapping accounts (clusters), 1000 resamples. | `src/ab.py` |

Tableau: Tableau itself is not runnable locally; `reports/dashboard_daily.csv`
and `reports/client_health.csv` are the Tableau-ready extracts and
`reports/dashboard.html` reproduces the same three views (attainment trend,
FRT trend, worst accounts) from the same marts.
