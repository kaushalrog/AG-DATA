"""Global LightGBM baseline on the fc_main_v3 protocol (reviewer-requested stronger ML baseline).

* Same feature table (data/forecast/features), panel, horizons and purged periods as fc_main_v3:
  train origins 2016-2023 (targets <= 2023-12-31), validation 2024 (targets <= 2024-12-31),
  test origins >= 2025-01-01.
* Same training budget: a uniform random sample of 2,000,000 training rows per horizon.
* Objective L1 (MAE, as the selection criterion). The commodity is a categorical feature.
* Tuning on VALIDATION only: num_leaves in {63, 255}, learning_rate 0.05, early stopping
  (100 rounds) on the validation MAE in log-return space, up to 3,000 rounds. Seeds {1, 2, 3}
  for the chosen configuration, so seed variance is reported.
* Scored once on the test rows of fc_main_v3 and compared with persistence and the selected
  MLlib model ON THE SAME ROWS (joined from data/forecast/test_predictions/fc_main_v3).

    .venv/bin/python -m agri.analysis.lgbm_baseline
Writes results/forecast/fc_main_v3/lgbm_baseline.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

FEATS = "data/forecast/features/*/*.parquet"
PRED = "data/forecast/test_predictions/fc_main_v3"
BASE = ["lp", "ret1", "ret2", "ret5", "gap1", "dev7", "dev30", "dev90", "std30", "std90", "cnt30", "cnt90",
        "hi30", "lo30", "spread", "ly_dev", "has_ly", "cs_dev30", "cs_ret1", "cs_n", "sc_dev30", "doy_sin", "doy_cos", "dow"]
H = {"next": 1, "h3": 3, "h7": 7, "h14": 14}


def load(con, h, start, end, limit=None, seed=20261022):
    cols = ", ".join(BASE + [f"ly_chg_{h}", "commodity", "entity_id", "arrival_date", "modal_price", f"y_{h}"])
    cond = f"in_panel AND y_{h} IS NOT NULL AND arrival_date >= DATE '{start}'"
    if end:
        cond += f" AND arrival_date <= DATE '{end}' AND tday_{h} <= {(pd.Timestamp(end) - pd.Timestamp('1970-01-01')).days}"
    q = f"SELECT {cols} FROM read_parquet('{FEATS}', hive_partitioning=true) WHERE {cond}"
    if limit:
        q = f"SELECT * FROM ({q}) USING SAMPLE reservoir({limit} ROWS) REPEATABLE ({seed % 100000})"
    df = con.execute(q).df()
    df[BASE + [f"ly_chg_{h}"]] = df[BASE + [f"ly_chg_{h}"]].fillna(0.0)
    df["commodity"] = df["commodity"].astype("category")
    return df


def rupee_mae(p0, y, yhat):
    return float(np.mean(np.abs(p0 * np.exp(yhat) - p0 * np.exp(y))))


def main() -> int:
    con = duckdb.connect(); con.execute("SET threads=8")
    out = {"protocol": "fc_main_v3 periods; 2M train sample; L1 objective; tuned on 2024 validation only; test scored once",
           "lightgbm_version": lgb.__version__, "horizons": {}}
    for h in H:
        t0 = time.time()
        tr = load(con, h, "2016-01-01", "2023-12-31", limit=2_000_000)
        va = load(con, h, "2024-01-01", "2024-12-31", limit=600_000)
        te = load(con, h, "2025-01-01", None)
        cats = pd.api.types.union_categoricals([tr["commodity"], va["commodity"], te["commodity"]]).categories
        for d in (tr, va, te):
            d["commodity"] = pd.Categorical(d["commodity"].astype(str), categories=cats)
        X = BASE + [f"ly_chg_{h}", "commodity"]
        y = f"y_{h}"
        best = None
        tuning = []
        for leaves in (63, 255):
            params = dict(objective="l1", learning_rate=0.05, num_leaves=leaves, min_data_in_leaf=200, feature_fraction=0.8,
                          bagging_fraction=0.7, bagging_freq=1, seed=1, verbose=-1, num_threads=8)
            m = lgb.train(params, lgb.Dataset(tr[X], tr[y]), num_boost_round=3000, valid_sets=[lgb.Dataset(va[X], va[y])],
                          callbacks=[lgb.early_stopping(100, verbose=False)])
            v = rupee_mae(va["modal_price"].values, va[y].values, m.predict(va[X], num_iteration=m.best_iteration))
            tuning.append({"num_leaves": leaves, "best_iteration": m.best_iteration, "val_mae": v})
            if best is None or v < best[0]:
                best = (v, params, m.best_iteration)
        # seeds for the chosen configuration (rounds fixed from validation)
        preds = []
        for seed in (1, 2, 3):
            p = dict(best[1], seed=seed)
            m = lgb.train(p, lgb.Dataset(tr[X], tr[y]), num_boost_round=best[2])
            preds.append(m.predict(te[X]))
        te["pred_lgbm"] = np.mean(preds, axis=0)
        seed_maes = [rupee_mae(te["modal_price"].values, te[y].values, p) for p in preds]
        # join with the MLlib test predictions on identical rows
        sel = con.execute(f"SELECT entity_id, arrival_date, pred_persistence, pred_selected FROM read_parquet('{PRED}/horizon={h}/*.parquet')").df()
        j = te.merge(sel, on=["entity_id", "arrival_date"], how="inner")
        p0, yy = j["modal_price"].values, j[y].values
        mp, ms, ml = (rupee_mae(p0, yy, j[c].values) for c in ("pred_persistence", "pred_selected", "pred_lgbm"))
        # daily loss differential vs the selected MLlib model (DM, HLN, lag h+3)
        from agri.analysis.forecast_report import dm_test
        j["e_l"] = np.abs(p0 * np.exp(j["pred_lgbm"]) - p0 * np.exp(yy)); j["e_s"] = np.abs(p0 * np.exp(j["pred_selected"]) - p0 * np.exp(yy))
        daily = j.groupby("arrival_date")[["e_l", "e_s"]].mean()
        st, pv = dm_test((daily["e_l"] - daily["e_s"]).values, 7 if h == "next" else H[h] + 3)
        out["horizons"][h] = {"tuning": tuning, "chosen_num_leaves": best[1]["num_leaves"], "rounds": best[2],
                              "test_rows_joined": len(j), "mae_persistence": mp, "mae_mllib_selected": ms, "mae_lgbm_3seed_mean": ml,
                              "rel_mae_mllib": ms / mp, "rel_mae_lgbm": ml / mp, "lgbm_seed_maes": seed_maes,
                              "dm_lgbm_vs_mllib": {"stat": st, "p": pv}, "seconds": round(time.time() - t0, 1)}
        print(h, json.dumps({k: v for k, v in out["horizons"][h].items() if k != "tuning"}))
    Path("results/forecast/fc_main_v3/lgbm_baseline.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
