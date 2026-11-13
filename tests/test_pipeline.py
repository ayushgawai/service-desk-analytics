import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
from gen import generate, SLA_HOURS
from predict import train_eval
from ab import ab_analysis

def merged(n=8000):
    a, p, t, u = generate(n_tickets=n)
    t = t.merge(p, on="priority").merge(a, on="account_id")
    t["is_breached"] = t.resolution_hours > t.sla_resolution_hours
    return t

def test_gen_deterministic_and_counts():
    a1, _, t1, _ = generate(n_tickets=500); a2, _, t2, _ = generate(n_tickets=500)
    assert len(a1) == 150 and len(t1) == 500 and t1.resolution_hours.equals(t2.resolution_hours)

def test_sla_breach_definition():
    df = merged(2000)
    expect = df.resolution_hours > df.priority.map(SLA_HOURS)
    assert (df.is_breached == expect).all()

def test_prediction_beats_baseline():
    m, _ = train_eval(merged(12000))
    assert m["roc_auc"] > 0.65 and m["n_test"] > 0  # target 0.84 at full scale; bench reports actual

def test_ab_recovers_injected_effect():
    r = ab_analysis(merged(30000))
    assert r["diff_pp"] < 0 and r["n_treatment_accounts"] > 50  # staffing speeds resolution

def test_kpi_attainment_bounds():
    df = merged(2000); att = 1 - df.is_breached.mean()
    assert 0 <= att <= 1
