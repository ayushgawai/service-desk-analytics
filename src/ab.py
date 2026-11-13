"""Staffing-change A/B: treatment vs control accounts after intervention day.
Outcome: SLA breach rate. Bootstrap CI resampling accounts (clusters),
tickets are not independent within an account."""
import numpy as np, pandas as pd

def ab_analysis(df, intervention_day=120, n_boot=1000, seed=7):
    df = df.copy(); df["created_at"] = pd.to_datetime(df["created_at"])
    start = df.created_at.min().normalize()
    df["day"] = (df.created_at - start).dt.days
    post = df[df.day >= intervention_day]
    # per-account breach rates keep clustering intact
    per = post.groupby(["account_id", "treatment"]).is_breached.mean().reset_index()
    t, c = per[per.treatment].is_breached, per[~per.treatment].is_breached
    diff = float(t.mean() - c.mean())
    rng = np.random.default_rng(seed); boots = []
    tv, cv = t.values, c.values
    for _ in range(n_boot):
        boots.append(rng.choice(tv, len(tv), True).mean() - rng.choice(cv, len(cv), True).mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"treatment_breach_rate": round(float(t.mean()), 4),
            "control_breach_rate": round(float(c.mean()), 4),
            "diff_pp": round(diff * 100, 2),
            "ci95_pp": [round(float(lo * 100), 2), round(float(hi * 100), 2)],
            "n_treatment_accounts": int(per.treatment.sum()),
            "n_control_accounts": int((~per.treatment).sum()),
            "significant": bool(lo > 0 or hi < 0)}
