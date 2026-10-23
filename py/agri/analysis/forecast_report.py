"""Statistical tests, tables and figures from a recorded forecasting experiment.

Everything here reads files written by ForecastBenchmark / ForecastBacktest;
nothing is re-estimated, so every number in the paper traces to those files.

Diebold-Mariano test: for each horizon, the loss differential is computed per
TEST DATE (sum of absolute errors of model A minus model B over all entities
reporting that day, divided by the number of rows), giving one time series
d_t. Aggregating per date avoids treating thousands of same-day, cross-
sectionally correlated errors as independent. The DM statistic uses a
Newey-West (Bartlett) long-run variance with lag = h + 3 (the target window's far
edge; 7 for `next`) and the
Harvey-Leybourne-Newbold small-sample correction; p-values are two-sided from
Student-t with T-1 df.

    .venv/bin/python -m agri.analysis.forecast_report --exp <experiment_id>
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

H_DAYS = {"next": 1, "h3": 3, "h7": 7, "h14": 14}
H_LABEL = {"next": "next obs.", "h3": "3 days", "h7": "7 days", "h14": "14 days"}


def read_csv(p: Path) -> list[dict]:
    with open(p) as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def dm_test(d: np.ndarray, lag: int) -> tuple[float, float]:
    T = len(d)
    dbar = d.mean()
    u = d - dbar
    gamma0 = (u @ u) / T
    lrv = gamma0 + 2 * sum((1 - k / (lag + 1)) * (u[k:] @ u[:-k]) / T for k in range(1, lag + 1))
    if lrv <= 0:
        return float("nan"), float("nan")
    dm = dbar / math.sqrt(lrv / T)
    h = lag
    hln = math.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    stat = dm * hln
    p = 2 * stats.t.sf(abs(stat), df=T - 1)
    return stat, p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--results", default="results/forecast")
    ap.add_argument("--paper", default="paper")
    a = ap.parse_args(argv)
    exp = Path(a.results) / a.exp
    figs = Path(a.paper) / "figures"; tabs = Path(a.paper) / "tables"
    figs.mkdir(parents=True, exist_ok=True); tabs.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((exp / "manifest.json").read_text())
    horizons = [h for h in manifest["horizons"]]
    overall = read_csv(exp / "metrics_overall.csv")

    # ---------------- DM tests ----------------
    dm_rows = []
    for h in horizons:
        rows = read_csv(exp / f"test_daily_loss_{h}.csv")
        by = {}
        for r in rows:
            by.setdefault(r["model"], {})[r["arrival_date"]] = (num(r["sum_abs_err"]), num(r["n"]))
        base = by.get("persistence", {})
        for m in sorted(by):
            if m == "persistence":
                continue
            dates = sorted(set(by[m]) & set(base))
            d = np.array([(by[m][t][0] - base[t][0]) / base[t][1] for t in dates])
            # targets lie up to h+3 days ahead (7 for `next`), so losses overlap for that long
            lag = 7 if h == "next" else H_DAYS[h] + 3
            stat, p = dm_test(d, lag)
            dm_rows.append({"horizon": h, "model": m, "vs": "persistence", "days": len(dates),
                            "mean_daily_mae_diff": float(d.mean()), "dm_stat": stat, "p_value": p})
    with open(exp / "dm_tests.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dm_rows[0].keys())); w.writeheader(); w.writerows(dm_rows)

    # ---------------- main table ----------------
    test = [r for r in overall if r["split"] == "test"]
    models = ["persistence", "ma7", "ma30", "snaive", "sadj", "lr", "rf", "gbt", "selected"]
    names = {"persistence": "Persistence (last obs.)", "ma7": "Moving avg. 7d", "ma30": "Moving avg. 30d",
             "snaive": "Seasonal naive", "sadj": "Seasonal-adjusted persistence", "lr": "Ridge regression (MLlib)",
             "rf": "Random forest (MLlib)", "gbt": "Gradient-boosted trees (MLlib)", "selected": "Selected on validation"}
    lines = ["| Horizon | Model | n | MAE (₹/q) | RMSE | WAPE % | sMAPE % | Bias | MASE | Rel. MAE | Dir. acc. |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    tex = []
    for h in horizons:
        for m in models:
            r = next((x for x in test if x["horizon"] == h and x["model"] == m), None)
            if not r:
                continue
            lines.append(f"| {H_LABEL[h]} | {names[m]} | {int(num(r['n'])):,} | {num(r['mae']):.1f} | {num(r['rmse']):.1f} | "
                         f"{100*num(r['wape']):.2f} | {100*num(r['smape']):.2f} | {num(r['bias']):+.1f} | {num(r['mase']):.3f} | "
                         f"{num(r['rel_mae_vs_persistence']):.3f} | {100*num(r['dir_acc']):.1f} |")
            tex.append(f"{H_LABEL[h]} & {names[m]} & {int(num(r['n'])):,} & {num(r['mae']):.1f} & {num(r['rmse']):.1f} & "
                       f"{100*num(r['wape']):.2f} & {num(r['mase']):.3f} & {num(r['rel_mae_vs_persistence']):.3f} \\\\")
    (tabs / "main_results.md").write_text(f"Experiment `{a.exp}` — TEST period {manifest['periods']['test'][0]}..{manifest['periods']['test'][1]}\n\n" + "\n".join(lines) + "\n")
    (tabs / "main_results.tex").write_text("\n".join(tex) + "\n")

    dm_lines = ["| Horizon | Model vs persistence | Test days | Mean daily ΔMAE (₹/q) | DM (HLN) | p |", "|---|---|---:|---:|---:|---:|"]
    for r in dm_rows:
        dm_lines.append(f"| {H_LABEL[r['horizon']]} | {r['model']} | {r['days']} | {r['mean_daily_mae_diff']:+.2f} | {r['dm_stat']:.2f} | {r['p_value']:.2g} |")
    (tabs / "dm_tests.md").write_text("\n".join(dm_lines) + "\n")

    # ---------------- figures ----------------
    plt.rcParams.update({"font.size": 9, "figure.dpi": 150})
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    show = ["persistence", "ma7", "snaive", "lr", "rf", "gbt"]
    x = np.arange(len(horizons)); wdt = 0.13
    for i, m in enumerate(show):
        vals = [num(next((r["mase"] for r in test if r["horizon"] == h and r["model"] == m), "nan")) for h in horizons]
        ax.bar(x + (i - len(show) / 2 + 0.5) * wdt, vals, wdt, label=names[m].split(" (")[0])
    ax.set_xticks(x, [H_LABEL[h] for h in horizons]); ax.set_ylabel("MASE (test)"); ax.axhline(1, color="k", lw=0.6, ls=":")
    ax.legend(fontsize=7, ncol=3); ax.set_title("Test MASE by horizon (lower is better)")
    fig.tight_layout(); fig.savefig(figs / "mase_by_horizon.png"); plt.close(fig)

    iv = read_csv(exp / "intervals.csv")
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    for h in horizons:
        g = [r for r in iv if r["horizon"] == h and r["group"].startswith("vol_bucket")]
        ax.plot([int(r["group"].split("_")[-1]) + 1 for r in g], [num(r["coverage80"]) for r in g], marker="o", label=H_LABEL[h])
    ax.axhline(0.8, color="k", lw=0.6, ls=":"); ax.set_xlabel("volatility quintile (std30, validation edges)")
    ax.set_ylabel("empirical coverage of 80% interval"); ax.set_ylim(0.5, 1.0); ax.legend(fontsize=7)
    ax.set_title("Conformal interval coverage on test"); fig.tight_layout(); fig.savefig(figs / "interval_coverage.png"); plt.close(fig)

    h = "h7" if "h7" in horizons else horizons[0]
    rows = read_csv(exp / f"test_by_commodity_{h}.csv")
    comm = sorted({r["commodity"] for r in rows})
    rel = []
    for c in comm:
        sel = next((num(r["mae"]) for r in rows if r["commodity"] == c and r["model"] == "selected"), float("nan"))
        per = next((num(r["mae"]) for r in rows if r["commodity"] == c and r["model"] == "persistence"), float("nan"))
        rel.append((c, sel / per))
    rel.sort(key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.barh([c for c, _ in rel], [v for _, v in rel], color=["#2e7d32" if v < 1 else "#c62828" for _, v in rel])
    ax.axvline(1, color="k", lw=0.6); ax.set_xlabel(f"MAE(selected) / MAE(persistence), {H_LABEL[h]} horizon, test")
    ax.tick_params(axis="y", labelsize=7); fig.tight_layout(); fig.savefig(figs / f"rel_mae_by_commodity_{h}.png"); plt.close(fig)

    daily = read_csv(exp / f"test_daily_loss_{h}.csv")
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    for m in ("persistence", "selected"):
        pts = sorted((r["arrival_date"], num(r["sum_abs_err"]) / num(r["n"])) for r in daily if r["model"] == m)
        if pts:
            t = np.array([np.datetime64(p[0]) for p in pts]); v = np.array([p[1] for p in pts])
            k = 7; vs = np.convolve(v, np.ones(k) / k, mode="same")
            ax.plot(t, vs, lw=1, label=m)
    ax.set_ylabel("daily MAE (₹/q), 7-day smoothed"); ax.legend(fontsize=7); ax.set_title(f"Test error over time ({H_LABEL[h]})")
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(figs / f"daily_mae_{h}.png"); plt.close(fig)

    # ---------------- sub-periods (AGMARKNET 2.0 migration, Nov 2025) ----------------
    pred_glob = Path(manifest["test_predictions_path"]) / "horizon=*" / "*.parquet"
    seg_lines = ["| Horizon | Sub-period | n | MAE persistence | MAE selected | Rel. MAE | 80% coverage |", "|---|---|---:|---:|---:|---:|---:|"]
    seg_rows = []
    if list(Path(manifest["test_predictions_path"]).glob("horizon=*")):
        import duckdb
        con = duckdb.connect()
        for h in horizons:
            y = f"y_{h}"
            q = f"""SELECT CASE WHEN arrival_date < DATE '2025-11-01' THEN '2025-01..2025-10' ELSE '2025-11..2026-04 (post-migration)' END seg,
                     count(*) n, avg(abs(modal_price*exp(pred_persistence) - modal_price*exp({y}))) mae_p,
                     avg(abs(modal_price*exp(pred_selected) - modal_price*exp({y}))) mae_s,
                     avg(CASE WHEN {y} BETWEEN lo80 AND hi80 THEN 1.0 ELSE 0.0 END) cov80
                   FROM read_parquet('{Path(manifest['test_predictions_path'])}/horizon={h}/*.parquet') GROUP BY 1 ORDER BY 1"""
            for seg, n, mp, ms, cov in con.execute(q).fetchall():
                seg_rows.append({"horizon": h, "segment": seg, "n": n, "mae_persistence": mp, "mae_selected": ms,
                                 "rel_mae": ms / mp, "coverage80": cov})
                seg_lines.append(f"| {H_LABEL[h]} | {seg} | {n:,} | {mp:.1f} | {ms:.1f} | {ms/mp:.3f} | {100*cov:.1f}% |")
        (tabs / "subperiods.md").write_text("\n".join(seg_lines) + "\n")

        # per-series wins (H1): share of entities (>= 30 test rows) where selected beats persistence on MAE
        win_lines = ["| Horizon | Series (≥30 test rows) | Selected better | Median per-series rel. MAE | P10 | P90 |",
                     "|---|---:|---:|---:|---:|---:|"]
        win_rows = []
        for h in horizons:
            y = f"y_{h}"
            r = con.execute(f"""WITH e AS (SELECT entity_id, count(*) n,
                    avg(abs(modal_price*exp(pred_selected) - modal_price*exp({y}))) ms,
                    avg(abs(modal_price*exp(pred_persistence) - modal_price*exp({y}))) mp
                  FROM read_parquet('{Path(manifest['test_predictions_path'])}/horizon={h}/*.parquet') GROUP BY 1 HAVING count(*) >= 30 AND mp > 0)
                SELECT count(*), avg((ms < mp)::INT), median(ms/mp), quantile_cont(ms/mp, 0.1), quantile_cont(ms/mp, 0.9) FROM e""").fetchone()
            win_rows.append({"horizon": h, "series": r[0], "share_selected_better": r[1], "median_rel": r[2], "p10": r[3], "p90": r[4]})
            win_lines.append(f"| {H_LABEL[h]} | {r[0]:,} | {100*r[1]:.1f}% | {r[2]:.3f} | {r[3]:.3f} | {r[4]:.3f} |")
        (tabs / "series_wins.md").write_text("\n".join(win_lines) + "\n")
        (exp / "test_series_wins.json").write_text(json.dumps(win_rows, indent=2))
        with open(exp / "test_subperiods.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(seg_rows[0].keys())); w.writeheader(); w.writerows(seg_rows)

    print(json.dumps({"dm_tests": dm_rows, "subperiods": seg_rows}, indent=1, default=float))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
