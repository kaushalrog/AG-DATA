"""LightGBM serving candidate (pre-registered in docs/PREREG_LGBM_SWITCH.md).

Produces an experiment that ForecastPublish can serve exactly like a Spark one:

  results/forecast/<exp>/manifest.json        selected_on_validation = "lgbm" per horizon, completed = true
  results/forecast/<exp>/conformal_<h>.csv    same layout as ForecastEval.fitConformal (5 std30 bins)
  results/forecast/<exp>/tuning.csv           validation MAE per num_leaves
  <models>/<exp>/<h>/lgbm/model.txt           LightGBM booster (best iteration only)
  <models>/<exp>/<h>/lgbm/meta.json           feature order and commodity categories

Commands:
  python -m agri.forecast.lgbm train  [--exp fc_lgbm_2025]
  python -m agri.forecast.lgbm test   [--exp fc_lgbm_2025]     # score the final test once
  python -m agri.forecast.lgbm score  --exp E --out P [--days 130]
      scores every in-panel feature row of the last N days and writes (entity_id, arrival_date,
      horizon, pred_lgbm) to P. ForecastPublish joins these when a horizon's selected model is lgbm.

Periods come from AGRI_TRAIN_END / AGRI_VAL_START / AGRI_VAL_END / AGRI_TEST_START, as in ForecastConfig.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

HORIZONS = {"next": 1, "h3": 3, "h7": 7, "h14": 14}
# Features.BaseFeatures, in the same order
BASE = ["lp", "ret1", "ret2", "ret5", "gap1", "dev7", "dev30", "dev90", "std30", "std90", "cnt30", "cnt90",
        "hi30", "lo30", "spread", "ly_dev", "has_ly", "cs_dev30", "cs_ret1", "cs_n", "sc_dev30", "doy_sin", "doy_cos", "dow"]
PARAMS = dict(objective="l1", learning_rate=0.05, min_data_in_leaf=200, feature_fraction=0.8,
              bagging_fraction=0.7, bagging_freq=1, seed=1, verbose=-1, num_threads=8)
LEAVES = (63, 255)
QUANTILES = (0.05, 0.10, 0.90, 0.95)
N_BUCKETS = 5
SAMPLE_SEED = 20261022


def env(k, d):
    return os.environ.get(k, d)


def periods():
    return {"train": [env("AGRI_TRAIN_START", "2016-01-01"), env("AGRI_TRAIN_END", "2024-12-31")],
            "validation": [env("AGRI_VAL_START", "2025-01-01"), env("AGRI_VAL_END", "2025-12-31")],
            "test_start": env("AGRI_TEST_START", "2026-01-01")}


def feats_glob(root):
    return f"{root}/features/*/*.parquet"


def features(h):
    return BASE + [f"ly_chg_{h}"]


def load(con, root, h, start, end=None, limit=None, labelled=True, extra=()):
    cols = ", ".join(features(h) + ["commodity", "entity_id", "arrival_date", "modal_price", "std30 AS std30_raw"]
                     + ([f"y_{h}"] if labelled else []) + list(extra))
    cond = f"in_panel AND arrival_date >= DATE '{start}'"
    if labelled:
        cond += f" AND y_{h} IS NOT NULL"
    if end:
        cond += f" AND arrival_date <= DATE '{end}'"
        if labelled:  # target purge, as ForecastBenchmark.periodFilter
            cond += f" AND tday_{h} <= {(pd.Timestamp(end) - pd.Timestamp('1970-01-01')).days}"
    q = f"SELECT {cols} FROM read_parquet('{feats_glob(root)}', hive_partitioning=true) WHERE {cond}"
    if limit:
        q = f"SELECT * FROM ({q}) USING SAMPLE reservoir({limit} ROWS) REPEATABLE ({SAMPLE_SEED % 100000})"
    df = con.execute(q).df()
    df[features(h)] = df[features(h)].fillna(0.0)  # Features.fillFeatureNulls
    df["std30_raw"] = df["std30_raw"].fillna(0.0)
    return df


def matrix(df, h, categories):
    X = df[features(h)].copy()
    X["commodity"] = pd.Categorical(df["commodity"].astype(str), categories=categories)
    return X


def rupee_mae(p0, y, yhat):
    return float(np.mean(np.abs(p0 * np.exp(yhat) - p0 * np.exp(y))))


def fit_conformal(std30, res):
    """Mirror of ForecastEval.fitConformal: bin edges at std30 quintiles, residual quantiles per bin."""
    edges = np.quantile(std30, [i / N_BUCKETS for i in range(1, N_BUCKETS)])
    b = bucket(std30, edges)
    q = {(k, p): float(np.quantile(res[b == k], p)) for k in range(N_BUCKETS) for p in QUANTILES}
    return edges, q


def bucket(std30, edges):
    # first edge e_i with std30 <= e_i; above every edge -> last bucket
    return np.searchsorted(edges, std30, side="left")


def intervals(pred, std30, edges, q):
    b = bucket(std30, edges)
    lookup = lambda p: np.array([q[(k, p)] for k in range(N_BUCKETS)])[b]
    return {"lo80": pred + lookup(0.10), "hi80": pred + lookup(0.90), "lo90": pred + lookup(0.05), "hi90": pred + lookup(0.95)}


def git_state():
    try:
        c = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        d = bool(subprocess.run(["git", "status", "--porcelain", "--", "py", "src"], capture_output=True, text=True).stdout.strip())
        return c, d
    except OSError:
        return None, None


def train(a) -> int:
    P = periods()
    con = duckdb.connect(); con.execute("SET threads=8")
    out = Path(a.results) / a.exp; out.mkdir(parents=True, exist_ok=True)
    tuning, sizes, cats_all = [], {}, None
    for h in HORIZONS:
        t0 = time.time()
        tr = load(con, a.features_root, h, P["train"][0], P["train"][1], limit=a.max_train_rows)
        va = load(con, a.features_root, h, P["validation"][0], P["validation"][1])
        cats = sorted(set(tr["commodity"].astype(str)) | set(va["commodity"].astype(str)))
        Xtr, Xva = matrix(tr, h, cats), matrix(va, h, cats)
        rng = np.random.default_rng(SAMPLE_SEED)
        tune_idx = rng.choice(len(va), size=min(len(va), a.max_tune_val_rows), replace=False)
        best = None
        for leaves in LEAVES:
            m = lgb.train(dict(PARAMS, num_leaves=leaves), lgb.Dataset(Xtr, tr[f"y_{h}"]), num_boost_round=3000,
                          valid_sets=[lgb.Dataset(Xva.iloc[tune_idx], va[f"y_{h}"].values[tune_idx])],
                          callbacks=[lgb.early_stopping(100, verbose=False)])
            v = rupee_mae(va["modal_price"].values[tune_idx], va[f"y_{h}"].values[tune_idx],
                          m.predict(Xva.iloc[tune_idx], num_iteration=m.best_iteration))
            tuning.append({"horizon": h, "num_leaves": leaves, "best_iteration": m.best_iteration, "val_mae_tune_sample": v})
            print(h, "leaves", leaves, "iter", m.best_iteration, "val MAE", round(v, 3), flush=True)
            if best is None or v < best[0]:
                best = (v, leaves, m)
        _, leaves, m = best
        pred_va = m.predict(Xva, num_iteration=m.best_iteration)
        edges, q = fit_conformal(va["std30_raw"].values, va[f"y_{h}"].values - pred_va)
        val_mae = rupee_mae(va["modal_price"].values, va[f"y_{h}"].values, pred_va)
        val_pers = rupee_mae(va["modal_price"].values, va[f"y_{h}"].values, np.zeros(len(va)))
        mdir = Path(a.models_root) / a.exp / h / "lgbm"; mdir.mkdir(parents=True, exist_ok=True)
        m.save_model(str(mdir / "model.txt"), num_iteration=m.best_iteration)
        (mdir / "meta.json").write_text(json.dumps({"features": features(h), "categorical": "commodity", "categories": cats,
                                                    "num_leaves": leaves, "num_iteration": m.best_iteration,
                                                    "lightgbm_version": lgb.__version__}, indent=1))
        with open(out / f"conformal_{h}.csv", "w") as f:  # ForecastPublish.readConformal layout
            f.write("horizon,bucket,quantile,residual_q,std30_upper_edge\n")
            for k in range(N_BUCKETS):
                e = edges[k] if k < len(edges) else float("inf")
                for p in QUANTILES:
                    f.write(f"{h},{k},{p:.7f},{q[(k, p)]:.9g},{'Infinity' if np.isinf(e) else f'{e:.9g}'}\n")
        sizes[h] = {"train_rows_sampled": len(tr), "val_rows": len(va), "val_mae": val_mae, "val_mae_persistence": val_pers,
                    "num_leaves": leaves, "num_iteration": m.best_iteration, "seconds": round(time.time() - t0, 1)}
        print(h, json.dumps(sizes[h]), flush=True)
    pd.DataFrame(tuning).to_csv(out / "tuning.csv", index=False)
    commit, dirty = git_state()
    manifest = {"experiment_id": a.exp, "family": "lightgbm", "completed": True,
                "selected_on_validation": {h: "lgbm" for h in HORIZONS}, "horizons": list(HORIZONS),
                "periods": {"train": P["train"], "validation": P["validation"], "test": [P["test_start"], None]},
                "params": PARAMS, "num_leaves_grid": list(LEAVES), "max_train_rows": a.max_train_rows,
                "max_tune_val_rows": a.max_tune_val_rows, "sample_seed": SAMPLE_SEED, "sizes": sizes,
                "dataset": {"features": a.features_root, "panel": "in_panel=true"},
                "models_path": f"{a.models_root}/{a.exp}", "preregistration": "docs/PREREG_LGBM_SWITCH.md",
                "git_commit": commit, "git_dirty": dirty, "created_utc": datetime.now(timezone.utc).isoformat(),
                "lightgbm_version": lgb.__version__}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


def load_model(models_root, exp, h):
    mdir = Path(models_root) / exp / h / "lgbm"
    meta = json.loads((mdir / "meta.json").read_text())
    return lgb.Booster(model_file=str(mdir / "model.txt")), meta


def read_conformal(path):
    c = pd.read_csv(path)
    edges = np.array(sorted({float(e) for e in c["std30_upper_edge"] if np.isfinite(float(e))}))
    q = {(int(r.bucket), round(float(r.quantile), 6)): float(r.residual_q) for r in c.itertuples()}
    return edges, {(k, p): q[(k, round(p, 6))] for k in range(N_BUCKETS) for p in QUANTILES}


def test(a) -> int:
    """Scores the final test ONCE and compares with frozen fc_main_v3 and fc_retrain_2025 on identical rows."""
    from agri.analysis.forecast_report import dm_test
    P = periods()
    con = duckdb.connect(); con.execute("SET threads=8")
    out = Path(a.results) / a.exp
    res = {"final_test_start": P["test_start"], "horizons": {}}
    rows_out, by_c, iv_rows = [], [], []
    for h, days in HORIZONS.items():
        booster, meta = load_model(a.models_root, a.exp, h)
        te = load(con, a.features_root, h, P["test_start"])
        te["pred_lgbm"] = booster.predict(matrix(te, h, meta["categories"]))
        edges, q = read_conformal(out / f"conformal_{h}.csv")
        iv = intervals(te["pred_lgbm"].values, te["std30_raw"].values, edges, q)
        te["lo80"], te["hi80"] = iv["lo80"], iv["hi80"]
        fz = con.execute(f"""SELECT entity_id, arrival_date, pred_selected AS pred_frozen, lo80 AS lo80_frozen, hi80 AS hi80_frozen
                             FROM read_parquet('{a.frozen_preds}/horizon={h}/*.parquet')""").df()
        rt = con.execute(f"""SELECT entity_id, arrival_date, pred_selected AS pred_retrained
                             FROM read_parquet('{a.retrained_preds}/horizon={h}/*.parquet')""").df()
        j = te.merge(fz, on=["entity_id", "arrival_date"]).merge(rt, on=["entity_id", "arrival_date"])
        p0, y = j["modal_price"].values, j[f"y_{h}"].values
        err = {k: np.abs(p0 * np.exp(j[c].values) - p0 * np.exp(y)) for k, c in
               (("lgbm", "pred_lgbm"), ("frozen", "pred_frozen"), ("retrained", "pred_retrained"))}
        err["persistence"] = np.abs(p0 - p0 * np.exp(y))
        daily = pd.DataFrame({"d": j["arrival_date"].values, **err}).groupby("d").mean()
        lag = 7 if h == "next" else days + 3
        dm = {}
        for other in ("frozen", "retrained", "persistence"):
            diff = (daily["lgbm"] - daily[other]).values
            st, p = dm_test(diff, lag)
            dm[other] = {"stat": st, "p": p, "mean_daily_diff": float(diff.mean()), "days": len(diff)}
        mae = {k: float(v.mean()) for k, v in err.items()}
        cov = lambda lo, hi: float(np.mean((y >= j[lo].values) & (y <= j[hi].values)))
        res["horizons"][h] = {"rows": len(j), "rows_lgbm_scored": len(te), "mae": mae,
                              "rel_mae": {k: mae[k] / mae["persistence"] for k in mae},
                              "coverage80": {"lgbm": cov("lo80", "hi80"), "frozen": cov("lo80_frozen", "hi80_frozen")},
                              "dm_lgbm_vs": dm}
        print(h, json.dumps({k: res["horizons"][h][k] for k in ("rows", "rel_mae", "coverage80")}), flush=True)
        rows_out.append(daily.assign(horizon=h))
        # files the API reads for per-commodity accuracy and coverage (all LightGBM test rows)
        a_ = te["modal_price"].values * np.exp(te[f"y_{h}"].values)
        for name, pr in (("selected", te["pred_lgbm"].values), ("persistence", np.zeros(len(te)))):
            e = np.abs(te["modal_price"].values * np.exp(pr) - a_)
            g = pd.DataFrame({"commodity": te["commodity"].values, "e": e, "a": a_}).groupby("commodity")
            by_c.append(pd.DataFrame({"n": g.size(), "mae": g["e"].mean(), "wape": g["e"].sum() / g["a"].sum()})
                        .reset_index().assign(model=name, horizon=h))
        yv = te[f"y_{h}"].values
        iv_rows.append({"horizon": h, "model": "lgbm", "group": "all", "n": len(te),
                        "coverage80": float(np.mean((yv >= iv["lo80"]) & (yv <= iv["hi80"]))),
                        "rel_width80": float(np.mean(np.exp(iv["hi80"]) - np.exp(iv["lo80"]))),
                        "coverage90": float(np.mean((yv >= iv["lo90"]) & (yv <= iv["hi90"]))),
                        "rel_width90": float(np.mean(np.exp(iv["hi90"]) - np.exp(iv["lo90"])))})
    bc = pd.concat(by_c)
    for h in HORIZONS:
        bc[bc.horizon == h].to_csv(out / f"test_by_commodity_{h}.csv", index=False)
    pd.DataFrame(iv_rows).to_csv(out / "intervals.csv", index=False)
    pd.concat(rows_out).to_csv(out / "final_test_daily_loss.csv")
    (out / "final_test_2026.json").write_text(json.dumps(res, indent=1))
    return 0


def score(a) -> int:
    """Predictions for recent feature rows; ForecastPublish joins them on (entity_id, arrival_date, horizon)."""
    con = duckdb.connect(); con.execute("SET threads=8")
    end = con.execute(f"SELECT max(arrival_date) FROM read_parquet('{feats_glob(a.features_root)}', hive_partitioning=true)").fetchone()[0]
    start = (pd.Timestamp(end) - pd.Timedelta(days=a.days)).date().isoformat()
    parts = []
    for h in HORIZONS:
        booster, meta = load_model(a.models_root, a.exp, h)
        # every recent row, labelled or not and in panel or not: publish forecasts all entities
        cols = ", ".join(features(h) + ["commodity", "entity_id", "arrival_date"])
        df = con.execute(f"SELECT {cols} FROM read_parquet('{feats_glob(a.features_root)}', hive_partitioning=true) "
                         f"WHERE arrival_date >= DATE '{start}'").df()
        df[features(h)] = df[features(h)].fillna(0.0)
        parts.append(pd.DataFrame({"entity_id": df["entity_id"].values, "arrival_date": pd.to_datetime(df["arrival_date"]).dt.date.values,
                                   "horizon": h, "pred_lgbm": booster.predict(matrix(df, h, meta["categories"]))}))
    out = pd.concat(parts, ignore_index=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(a.out, index=False)
    print(f"scored {len(out)} rows ({start} .. {end}) -> {a.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "test", "score"])
    ap.add_argument("--exp", default="fc_lgbm_2025")
    ap.add_argument("--features-root", default=env("AGRI_FORECAST_ROOT", "data/forecast_v3"))
    ap.add_argument("--models-root", default=env("AGRI_MODELS_ROOT", "data/forecast_v3/models"))
    ap.add_argument("--results", default=env("AGRI_RESULTS_ROOT", "results/forecast"))
    ap.add_argument("--max-train-rows", type=int, default=2_000_000)
    ap.add_argument("--max-tune-val-rows", type=int, default=600_000)
    ap.add_argument("--frozen-preds", default="data/forecast_v3/test_predictions/fc_main_v3/final_test_2026")
    ap.add_argument("--retrained-preds", default="data/forecast_v3/test_predictions/fc_retrain_2025")
    ap.add_argument("--out", default=None)
    ap.add_argument("--days", type=int, default=130)
    a = ap.parse_args(argv)
    if a.cmd == "score" and not a.out:
        ap.error("score needs --out")
    return {"train": train, "test": test, "score": score}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
