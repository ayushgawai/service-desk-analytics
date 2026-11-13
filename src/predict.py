"""SLA breach prediction. Features are known at ticket creation only
(no leakage: no resolution/first-response values). Time-based holdout."""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

FEATURES = ["priority", "category", "channel", "complexity_score", "tier",
            "seats", "created_hour", "created_dow"]

def add_features(df):
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["created_hour"] = df.created_at.dt.hour
    df["created_dow"] = df.created_at.dt.day_of_week
    return df

def train_eval(df, cutoff_q=0.8):
    df = add_features(df).sort_values("created_at")
    cut = df.created_at.quantile(cutoff_q)
    tr, te = df[df.created_at <= cut], df[df.created_at > cut]
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"),
                              ["priority", "category", "channel", "tier"])],
                            remainder="passthrough")
    model = Pipeline([("pre", pre), ("clf", HistGradientBoostingClassifier(random_state=7))])
    model.fit(tr[FEATURES], tr["is_breached"])
    p = model.predict_proba(te[FEATURES])[:, 1]
    return {"roc_auc": round(float(roc_auc_score(te.is_breached, p)), 4),
            "brier": round(float(brier_score_loss(te.is_breached, p)), 4),
            "n_train": len(tr), "n_test": len(te), "cutoff": str(cut.date()),
            "test_breach_rate": round(float(te.is_breached.mean()), 4)}, model
