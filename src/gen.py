"""Synthetic data: 150 accounts, support tickets, uptime checks, SLA policies.
Deterministic (seeded). Staffing A/B: treatment accounts get 15% faster
first-response/resolution after day 120 (the intervention under test).
"""
import numpy as np, pandas as pd

PRIORITIES = ["P1", "P2", "P3", "P4"]
SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}          # resolution target
FRT_MIN = {"P1": 15, "P2": 30, "P3": 120, "P4": 480}        # first-response target

def generate(n_tickets=120_000, n_accounts=150, days=180, seed=7, start="2025-01-01"):
    rng = np.random.default_rng(seed)
    tiers = rng.choice(["enterprise", "mid", "smb"], n_accounts, p=[.2, .4, .4])
    accounts = pd.DataFrame({
        "account_id": [f"A{i:03d}" for i in range(n_accounts)],
        "tier": tiers,
        "seats": rng.integers(20, 5000, n_accounts),
        "region": rng.choice(["NA", "EU", "APAC"], n_accounts),
        "treatment": rng.random(n_accounts) < 0.5,  # staffing-change A/B assignment
    })
    policies = pd.DataFrame({"priority": PRIORITIES,
        "sla_resolution_hours": [SLA_HOURS[p] for p in PRIORITIES],
        "sla_first_response_minutes": [FRT_MIN[p] for p in PRIORITIES]})

    acct = rng.integers(0, n_accounts, n_tickets)
    tier = accounts.tier.values[acct]
    created_day = rng.integers(0, days, n_tickets)
    created = (pd.Timestamp(start) + pd.to_timedelta(created_day, "D")
               + pd.to_timedelta(rng.random(n_tickets) * 24, "h"))
    priority = rng.choice(PRIORITIES, n_tickets, p=[.08, .27, .4, .25])
    complexity = np.clip(rng.normal(1.0, .45, n_tickets), .2, 2.5)  # known at intake
    base = {"P1": 2.5, "P2": 5, "P3": 14, "P4": 40}
    scale = np.array([base[p] for p in priority]) * complexity
    scale *= np.where(tier == "enterprise", .85, np.where(tier == "smb", 1.15, 1.0))
    # intervention: treatment accounts, after day 120
    treated = accounts.treatment.values[acct] & (created_day >= 120)
    scale *= np.where(treated, .82, 1.0)
    res_h = rng.lognormal(np.log(scale), .38)
    frt_m = res_h * rng.uniform(.03, .2, n_tickets) * 60
    tickets = pd.DataFrame({
        "ticket_id": np.arange(1, n_tickets + 1),
        "account_id": accounts.account_id.values[acct],
        "created_at": created, "priority": priority,
        "category": rng.choice(["access", "bug", "billing", "howto", "outage"], n_tickets),
        "channel": rng.choice(["email", "chat", "phone", "portal"], n_tickets),
        "complexity_score": complexity.round(3),
        "first_response_minutes": frt_m.round(1),
        "resolution_hours": res_h.round(2),
    })
    tickets["resolved_at"] = tickets.created_at + pd.to_timedelta(tickets.resolution_hours, "h")
    tickets["status"] = "closed"

    # daily uptime checks per account (1-min synthetic probe aggregated daily)
    up = pd.DataFrame({"account_id": np.repeat(accounts.account_id, days),
                       "check_date": np.tile(pd.date_range(start, periods=days), n_accounts)})
    up["uptime_pct"] = np.clip(rng.normal(99.7, .35, len(up)), 95, 100).round(3)
    return accounts, policies, tickets, up

def write_all(out="data/raw", **kw):
    import os; os.makedirs(out, exist_ok=True)
    a, p, t, u = generate(**kw)
    for name, df in [("accounts", a), ("sla_policies", p), ("tickets", t), ("uptime_checks", u)]:
        df.to_csv(f"{out}/{name}.csv", index=False)
    return {"accounts": len(a), "tickets": len(t), "uptime_checks": len(u)}
