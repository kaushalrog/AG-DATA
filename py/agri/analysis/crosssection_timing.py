"""Does the same-day cross-market information leak? (reviewer risk: publication timing)

Re-fits the LightGBM baseline (configuration and rounds fixed from lgbm_baseline.json, seed 1)
with three versions of the cross-market features, on the fc_main_v3 protocol:
  same_day  : as published in the feature table (other markets' reports of day t)
  lag1      : the previous calendar day's values (published before the origin day)
  none      : cross-market features removed
The lagged aggregates are recomputed from the feature table over all entities, exactly as
ForecastBenchmark crossSection=lag1 does. Writes results/forecast/fc_main_v3/crosssection_timing.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

from agri.analysis.lgbm_baseline import BASE, FEATS, rupee_mae

CS = ["cs_dev30", "cs_ret1", "cs_n", "sc_dev30"]


def load(con, h, start, end, lag, limit=None):
    keep = [c for c in BASE if c not in CS]
    cols = ", ".join(f"f.{c}" for c in keep + [f"ly_chg_{h}", "commodity", "state", "day", "arrival_date", "modal_price", f"y_{h}"])
    cond = f"f.in_panel AND f.y_{h} IS NOT NULL AND f.arrival_date >= DATE '{start}'"
    if end:
        cond += f" AND f.arrival_date <= DATE '{end}' AND f.tday_{h} <= {(pd.Timestamp(end) - pd.Timestamp('1970-01-01')).days}"
    if lag == "lag1":
        cs = ", c.cs_dev30, c.cs_ret1, c.cs_n, s.sc_dev30"
        join = """LEFT JOIN cs c ON c.commodity = f.commodity AND c.day = f.day - 1
                  LEFT JOIN sc s ON s.state = f.state AND s.commodity = f.commodity AND s.day = f.day - 1"""
    elif lag == "same_day":
        cs, join = ", f.cs_dev30, f.cs_ret1, f.cs_n, f.sc_dev30", ""
    else:
        cs, join = "", ""
    q = f"SELECT {cols}{cs} FROM read_parquet('{FEATS}', hive_partitioning=true) f {join} WHERE {cond}"
    if limit:
        q = f"SELECT * FROM ({q}) USING SAMPLE reservoir({limit} ROWS) REPEATABLE (61022)"
    df = con.execute(q).df()
    num = [c for c in df.columns if c not in ("commodity", "state", "day", "arrival_date", "modal_price", f"y_{h}")]
    df[num] = df[num].fillna(0.0)
    return df, num


def main() -> int:
    con = duckdb.connect(); con.execute("SET threads=8")
    con.execute(f"""CREATE TABLE cs AS SELECT commodity, day, avg(dev30) cs_dev30, avg(ret1) cs_ret1, count(*)::DOUBLE cs_n
                    FROM read_parquet('{FEATS}', hive_partitioning=true) GROUP BY 1, 2""")
    con.execute(f"""CREATE TABLE sc AS SELECT state, commodity, day, avg(dev30) sc_dev30
                    FROM read_parquet('{FEATS}', hive_partitioning=true) GROUP BY 1, 2, 3""")
    base = json.loads(Path("results/forecast/fc_main_v3/lgbm_baseline.json").read_text())["horizons"]
    out = {"protocol": "fc_main_v3 periods; LightGBM L1, num_leaves and rounds fixed from lgbm_baseline.json; seed 1",
           "horizons": {}}
    for h in ("next", "h7", "h14"):
        res = {}
        for lag in ("same_day", "lag1", "none"):
            t0 = time.time()
            tr, num = load(con, h, "2016-01-01", "2023-12-31", lag, limit=2_000_000)
            te, _ = load(con, h, "2025-01-01", None, lag)
            cats = pd.api.types.union_categoricals([tr["commodity"].astype("category"), te["commodity"].astype("category")]).categories
            for d in (tr, te):
                d["commodity"] = pd.Categorical(d["commodity"].astype(str), categories=cats)
            X = num + ["commodity"]
            p = dict(objective="l1", learning_rate=0.05, num_leaves=base[h]["chosen_num_leaves"], min_data_in_leaf=200,
                     feature_fraction=0.8, bagging_fraction=0.7, bagging_freq=1, seed=1, verbose=-1, num_threads=8)
            m = lgb.train(p, lgb.Dataset(tr[X], tr[f"y_{h}"]), num_boost_round=base[h]["rounds"])
            pers = rupee_mae(te["modal_price"].values, te[f"y_{h}"].values, np.zeros(len(te)))
            mae = rupee_mae(te["modal_price"].values, te[f"y_{h}"].values, m.predict(te[X]))
            res[lag] = {"test_rows": len(te), "mae": mae, "mae_persistence": pers, "rel_mae": mae / pers, "seconds": round(time.time() - t0, 1)}
            print(h, lag, json.dumps(res[lag]), flush=True)
        out["horizons"][h] = res
        Path("results/forecast/fc_main_v3/crosssection_timing.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
