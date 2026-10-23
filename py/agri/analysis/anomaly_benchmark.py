"""Anomaly-detection evaluation with INJECTED, labelled corruptions.

There is no ground-truth label for "anomalous mandi price" in the archive, so
we cannot claim accuracy on real anomalies. Instead we measure how well each
detector recovers corruptions that we inject ourselves into real 2025 test-period
series (panel entities). Two corruption families:

  data_error   modal price multiplied by 10, 100 or 0.1 (unit / keying slips)
  shock        modal price moved by +-35..60% (an abrupt market move)

Only the corrupted value is changed; the trailing reference statistics are
computed from the ORIGINAL history before the scored day, exactly as the
online rule would see it.

Detectors (higher score = more anomalous):
  trailing_z     |ln P - mean30_prev| / max(std30_prev, 0.03)    (the production rule's score)
  prev_change    |ln P - ln P_prev|                               (simple baseline)
  commodity_iqr  distance of P outside the commodity's TRAIN-period [Q1-3IQR, Q3+3IQR], in IQR units
                 (the previous project's outlier rule, re-fitted on 2016-2023 only)

Metrics: prevalence, PR-AUC (average precision), precision/recall/F1 and
false-positive rate at each detector's operating point, plus the production
rule's decision (alert types price_spike/price_drop/suspect_data_error).
Writes results/anomaly/<run>/metrics.csv and summary.json.

    .venv/bin/python -m agri.analysis.anomaly_benchmark --sample 400000 --rate 0.01
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

FEATS = "data/forecast/features/*/*.parquet"
Z_T, MIN_STD, MIN_MOVE, ERR_MOVE = 3.5, 0.03, math.log(1.2), math.log(5.0)


def average_precision(y: np.ndarray, s: np.ndarray) -> float:
    order = np.argsort(-s, kind="mergesort")
    y = y[order]
    tp = np.cumsum(y)
    prec = tp / np.arange(1, len(y) + 1)
    return float((prec * y).sum() / max(y.sum(), 1))


def prf(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int((pred & y).sum()); fp = int((pred & ~y).sum()); fn = int((~pred & y).sum()); tn = int((~pred & ~y).sum())
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if tp else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": p, "recall": r, "f1": f, "fpr": fp / (fp + tn)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=400_000)
    ap.add_argument("--rate", type=float, default=0.01, help="share of scored rows corrupted")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default="results/anomaly")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(a.seed)
    con = duckdb.connect()
    con.execute("SET threads=4")
    # trailing stats strictly before each row (RANGE over integer day numbers)
    df = con.execute(f"""SELECT * FROM (
        WITH f AS (SELECT entity_id, commodity, day, lp FROM read_parquet('{FEATS}', hive_partitioning=true)
                   WHERE in_panel AND arrival_date >= '2024-11-01')
        SELECT entity_id, commodity, day, lp,
               avg(lp) OVER w AS m, stddev_samp(lp) OVER w AS s,
               lag(lp) OVER (PARTITION BY entity_id ORDER BY day) AS lp_prev
        FROM f WINDOW w AS (PARTITION BY entity_id ORDER BY day RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING)
        QUALIFY day >= {(datetime(2025, 1, 1) - datetime(1970, 1, 1)).days} AND m IS NOT NULL AND lp_prev IS NOT NULL)
        USING SAMPLE reservoir({a.sample} ROWS) REPEATABLE ({a.seed})""").df()
    iqr = con.execute(f"""SELECT commodity, quantile_cont(exp(lp), 0.25) q1, quantile_cont(exp(lp), 0.75) q3
        FROM read_parquet('{FEATS}', hive_partitioning=true) WHERE in_panel AND arrival_date BETWEEN '2016-01-01' AND '2023-12-31'
        GROUP BY 1""").df().set_index("commodity")

    n = len(df)
    kind = np.array(["none"] * n, dtype=object)
    idx = rng.choice(n, size=int(n * a.rate), replace=False)
    half = len(idx) // 2
    lp = df["lp"].to_numpy().copy()
    err = idx[:half]; shock = idx[half:]
    lp[err] += np.log(rng.choice([10.0, 100.0, 0.1], size=len(err)))
    lp[shock] += np.log1p(rng.choice([-1, 1], size=len(shock)) * rng.uniform(0.35, 0.60, size=len(shock)))
    kind[err] = "data_error"; kind[shock] = "shock"

    m = df["m"].to_numpy(); s = np.nan_to_num(df["s"].to_numpy(), nan=MIN_STD)
    dev = lp - m
    z = dev / np.maximum(s, MIN_STD)
    price = np.exp(lp)
    q1 = df["commodity"].map(iqr["q1"]).to_numpy(); q3 = df["commodity"].map(iqr["q3"]).to_numpy()
    w = np.maximum(q3 - q1, 1e-9)
    iqr_score = np.maximum((price - (q3 + 3 * w)) / w, ((q1 - 3 * w) - price) / w).clip(min=0)
    scores = {"trailing_z": np.abs(z), "prev_change": np.abs(lp - df["lp_prev"].to_numpy()), "commodity_iqr": iqr_score}
    ops = {"trailing_z": np.abs(z) > Z_T, "prev_change": np.abs(lp - df["lp_prev"].to_numpy()) > math.log(1.35),
           "commodity_iqr": iqr_score > 0}
    rule = (np.abs(dev) > ERR_MOVE) | ((z > Z_T) & (dev > MIN_MOVE)) | ((z < -Z_T) & (dev < -MIN_MOVE))
    ops["production_rule"] = rule
    scores["production_rule"] = np.abs(z) * (np.abs(dev) > MIN_MOVE)

    rows = []
    for target in ("any", "data_error", "shock"):
        if target == "any":
            y = kind != "none"; mask = np.ones(n, bool)
        else:  # evaluate each family against clean rows only
            y = kind == target; mask = (kind == target) | (kind == "none")
        for name in scores:
            r = prf(y[mask], ops[name][mask])
            rows.append({"target": target, "detector": name, "n": int(mask.sum()), "prevalence": float(y[mask].mean()),
                         "pr_auc": average_precision(y[mask], scores[name][mask]), **r})
    # base rate of the production rule on UNCORRUPTED real rows (no accuracy claim: no labels)
    clean = kind == "none"
    real_rate = float(ops["production_rule"][clean].mean())

    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(a.out) / run
    out.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys())
    (out / "metrics.csv").write_text(",".join(keys) + "\n" + "\n".join(",".join(f"{r[k]:.6g}" if isinstance(r[k], float) else str(r[k]) for k in keys) for r in rows) + "\n")
    summary = {"run": run, "rows_scored": n, "corruption_rate": a.rate, "seed": a.seed, "period": "2025-01-01..data end",
               "population": "panel entities, 36 commodities", "injected": {"data_error": int(half), "shock": int(len(idx) - half)},
               "production_rule_flag_rate_on_uncorrupted_rows": real_rate,
               "note": "Labels are injected corruptions, not real anomalies. Flags on uncorrupted rows are not false positives in "
                       "any verified sense: some may be genuine market events.", "metrics": rows}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
