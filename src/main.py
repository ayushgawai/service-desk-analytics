"""CLI: gen | load | dbt | predict | ab | dashboard | bench | all"""
import argparse, json, os, subprocess, sys, time
import duckdb, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from gen import write_all, SLA_HOURS
from predict import train_eval
from ab import ab_analysis

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def p(*a): return os.path.join(ROOT, *a)

def load_raw(db=p("warehouse.duckdb")):
    con = duckdb.connect(db)
    for t in ["accounts", "tickets", "sla_policies", "uptime_checks"]:
        con.execute(f"CREATE OR REPLACE TABLE raw_{t} AS SELECT * FROM read_csv_auto('{p('data/raw')}/{t}.csv')")
    con.close()

def load_fct():
    con = duckdb.connect(p("warehouse.duckdb"), read_only=True)
    df = con.execute("select * from fct_tickets").df(); con.close(); return df

def run_dbt():
    import shutil
    exe = shutil.which("dbt") or p(".venv/bin/dbt")
    subprocess.run([exe, "run", "--project-dir", p("dbt"), "--profiles-dir", p("dbt")],
                   check=True, cwd=ROOT)

def _has_marts():
    try:
        con = duckdb.connect(p("warehouse.duckdb"), read_only=True)
        ok = con.execute("select count(*) from information_schema.tables where table_name='fct_tickets'").fetchone()[0] > 0
        con.close(); return ok
    except Exception: return False

def dashboard(df_fct=None):
    con = duckdb.connect(p("warehouse.duckdb"), read_only=True)
    daily = con.execute("select cast(created_at as date) as day, 1-avg(case when is_breached then 1.0 else 0 end) sla, "
                        "median(first_response_minutes) frt, count(*) n from fct_tickets group by 1 order by 1").df()
    health = con.execute("select * from agg_client_health").df(); con.close()
    daily.to_csv(p("reports/dashboard_daily.csv"), index=False)
    health.to_csv(p("reports/client_health.csv"), index=False)  # Tableau-ready extracts
    pts = " ".join(f"{i*4},{120-v*100:.1f}" for i, v in enumerate(daily.sla))
    bars = "".join(f'<rect x="{i*8}" y="{120-min(v,120):.0f}" width="6" height="{min(v,120):.0f}" fill="#4f7cff"/>'
                   for i, v in enumerate((daily.frt / daily.frt.max() * 120)))
    rows = "".join(f"<tr><td>{r.account_id}</td><td>{r.tickets}</td><td>{r.sla_attainment:.3f}</td>"
                   f"<td>{r.median_frt_min:.0f}</td><td>{r.avg_uptime_pct:.2f}</td><td>{r.health_band}</td></tr>"
                   for r in health.sort_values("sla_attainment").head(20).itertuples())
    html = f"""<!doctype html><meta charset=utf-8><title>Service Desk Analytics</title>
<style>body{{font-family:system-ui;margin:2rem;background:#0f1420;color:#e8ecf4}}svg{{background:#1a2233;width:100%}}
table{{border-collapse:collapse}}td,th{{border:1px solid #334;padding:4px 8px}}</style>
<h1>Service Desk Analytics</h1>
<p>Overall SLA attainment: <b>{daily.sla.mean():.1%}</b> · Median FRT (latest day): <b>{daily.frt.iloc[-1]:.0f} min</b>
· Open definition notes: docs/kpis.md · Tableau extracts: reports/dashboard_daily.csv, reports/client_health.csv</p>
<h2>SLA attainment by day</h2><svg viewBox="0 0 720 120" preserveAspectRatio="none"><polyline fill="none" stroke="#3ddc84" stroke-width="2" points="{pts}"/></svg>
<h2>Median first-response minutes by day (scaled)</h2><svg viewBox="0 0 1440 120" preserveAspectRatio="none">{bars}</svg>
<h2>20 lowest-SLA accounts</h2><table><tr><th>account</th><th>tickets</th><th>SLA</th><th>FRT min</th><th>uptime%</th><th>health</th></tr>{rows}</table>"""
    open(p("reports/dashboard.html"), "w").write(html)

def bench(n=120_000):
    t0 = time.time(); counts = write_all(p("data/raw"), n_tickets=n)
    t1 = time.time(); load_raw(); run_dbt(); t2 = time.time()
    df = load_fct(); pred, _ = train_eval(df); ab = ab_analysis(df); dashboard()
    out = {"scale": counts, "gen_s": round(t1-t0, 2), "dbt_s": round(t2-t1, 2),
           "total_s": round(time.time()-t0, 2), "prediction": pred, "ab": ab}
    os.makedirs(p("reports"), exist_ok=True)
    json.dump(out, open(p("reports/bench.json"), "w"), indent=2, default=str)
    # one-page recommendations
    open(p("reports/recommendation_prediction.md"), "w").write(
        f"# Recommendation: staff to predicted breach risk\n\nTime-holdout ROC AUC {pred['roc_auc']} "
        f"(target 0.84, breach rate {pred['test_breach_rate']:.1%}). Route tickets scoring in the top "
        "risk decile at creation to senior queue + proactive status ping at 50% of SLA budget.\n")
    open(p("reports/recommendation_staffing.md"), "w").write(
        f"# Recommendation: keep the staffing change\n\nPost-change breach-rate difference "
        f"{ab['diff_pp']}pp (95% CI {ab['ci95_pp']}pp, treatment {ab['treatment_breach_rate']:.1%} vs "
        f"control {ab['control_breach_rate']:.1%}). Significant: {ab['significant']}. Keep the change; "
        "recheck after one more quarter.\n")
    print(json.dumps(out, indent=2, default=str)); return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="service-desk-analytics")
    ap.add_argument("cmd", choices=["gen", "load", "dbt", "predict", "ab", "dashboard", "bench", "all"])
    ap.add_argument("--tickets", type=int, default=120_000)
    a = ap.parse_args()
    if a.cmd == "gen": print(write_all(p("data/raw"), n_tickets=a.tickets))
    elif a.cmd == "load": load_raw()
    elif a.cmd == "dbt": run_dbt()
    elif a.cmd == "predict": print(json.dumps(train_eval(load_fct())[0], indent=2))
    elif a.cmd == "ab": print(json.dumps(ab_analysis(load_fct()), indent=2))
    elif a.cmd == "dashboard": dashboard()
    elif a.cmd in ("bench", "all"): bench(a.tickets)
