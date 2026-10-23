"""Per-series statistical baseline: simple exponential smoothing (SES) on log price.

Classical per-series models (ETS/ARIMA) are fitted one series at a time, which
is not what the distributed pipeline is for. So this baseline runs on a RANDOM
SAMPLE of panel series and is compared with persistence and the selected global
model on exactly the same test rows (joined from the persisted test predictions).

For each sampled entity:
  * alpha in {0.05, 0.1, ..., 1.0} is chosen to minimise the in-sample MAE of the
    h-step SES forecast on TRAINING origins (2016-2023) only;
  * the level is run forward over the whole series (the level at t uses reports <= t);
  * the forecast for every horizon is the level at the origin (SES has a flat forecast).
alpha = 1 is persistence, so SES can only differ from persistence where smoothing helps.

    .venv/bin/python -m agri.analysis.stat_baseline --exp fc_main_v2 --entities 400
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np

ALPHAS = np.round(np.arange(0.05, 1.0001, 0.05), 2)
TRAIN_END = np.datetime64("2023-12-31")


def ses_levels(lp: np.ndarray, alpha: float) -> np.ndarray:
    lev = np.empty_like(lp)
    lev[0] = lp[0]
    for i in range(1, len(lp)):
        lev[i] = alpha * lp[i] + (1 - alpha) * lev[i - 1]
    return lev


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--entities", type=int, default=400)
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args(argv)
    con = duckdb.connect()
    con.execute("SET threads=4")
    feats = "data/forecast/features/*/*.parquet"
    preds = f"data/forecast/test_predictions/{a.exp}"
    ents = [r[0] for r in con.execute(
        f"SELECT DISTINCT entity_id FROM read_parquet('{preds}/horizon=h7/*.parquet') ORDER BY hash(entity_id + {a.seed}) LIMIT {a.entities}").fetchall()]
    con.execute("CREATE TEMP TABLE ents AS SELECT unnest(?) AS entity_id", [ents])
    series = con.execute(f"""SELECT entity_id, arrival_date, lp, y_next, y_h3, y_h7, y_h14 FROM read_parquet('{feats}', hive_partitioning=true)
                            WHERE entity_id IN (SELECT entity_id FROM ents) AND arrival_date >= '2016-01-01'
                            ORDER BY entity_id, arrival_date""").df()
    out_rows = []
    for h in ("next", "h3", "h7", "h14"):
        y = f"y_{h}"
        fc = []
        for eid, g in series.groupby("entity_id", sort=False):
            lp = g["lp"].to_numpy(); yy = g[y].to_numpy(); dates = g["arrival_date"].to_numpy().astype("datetime64[D]")
            tr = (dates <= TRAIN_END) & ~np.isnan(yy)
            if tr.sum() < 30:
                continue
            best, best_err = 1.0, np.inf
            for al in ALPHAS:
                lev = ses_levels(lp, al)
                err = np.mean(np.abs(np.exp(lp[tr] + yy[tr]) - np.exp(lev[tr])))
                if err < best_err:
                    best, best_err = al, err
            lev = ses_levels(lp, best)
            te = dates >= np.datetime64("2025-01-01")
            for d, l, p in zip(dates[te], lev[te], lp[te]):
                fc.append((eid, str(d), float(l - p), float(best)))
        con.execute("CREATE OR REPLACE TEMP TABLE ses(entity_id BIGINT, d DATE, pred_ses DOUBLE, alpha DOUBLE)")
        con.executemany("INSERT INTO ses VALUES (?, ?, ?, ?)", fc)
        r = con.execute(f"""SELECT count(*) n,
              avg(abs(modal_price*exp(pred_persistence) - modal_price*exp({y}))) mae_persistence,
              avg(abs(modal_price*exp(s.pred_ses) - modal_price*exp({y}))) mae_ses,
              avg(abs(modal_price*exp(pred_selected) - modal_price*exp({y}))) mae_selected,
              avg(s.alpha) mean_alpha, count(DISTINCT p.entity_id) entities
            FROM read_parquet('{preds}/horizon={h}/*.parquet') p JOIN ses s ON p.entity_id = s.entity_id AND p.arrival_date = s.d""").fetchone()
        row = dict(zip(["n", "mae_persistence", "mae_ses", "mae_selected", "mean_alpha", "entities"], r))
        row.update({"horizon": h, "rel_mae_ses": row["mae_ses"] / row["mae_persistence"],
                    "rel_mae_selected": row["mae_selected"] / row["mae_persistence"]})
        out_rows.append(row)
        print(json.dumps(row))
    p = Path(f"results/forecast/{a.exp}/stat_baseline_ses.json")
    p.write_text(json.dumps({"sampled_entities": len(ents), "seed": a.seed, "alpha_grid": ALPHAS.tolist(),
                             "selection": "alpha minimising in-sample MAE on 2016-2023 origins", "rows": out_rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
