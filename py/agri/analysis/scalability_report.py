"""Figures and tables from results/scalability/runs.jsonl (ScalabilityBench)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main() -> int:
    runs = [json.loads(l) for l in Path("results/scalability/runs.jsonl").read_text().splitlines() if l.strip()]
    local = [r for r in runs if r["master"].startswith("local")]
    figs = Path("paper/figures"); figs.mkdir(parents=True, exist_ok=True)
    size = {}
    for r in local:
        if r["cores"] == 10 and r["shuffle_partitions"] == "32" and r["aqe"] == "true":
            size.setdefault(r["workload"], {}).setdefault(r["rows_in"], r["seconds"])  # first (size-sweep) run wins
    cores = {}
    for r in local:
        if r.get("years") == "2018-2025" and r["master"].startswith("local["):
            cores.setdefault(r["workload"], {})[r["cores"]] = r["seconds"]
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for w, pts in size.items():
        xs = sorted(pts); ax[0].plot([x / 1e6 for x in xs], [pts[x] for x in xs], marker="o", label=w)
    ax[0].set_xlabel("input rows (millions, real silver)"); ax[0].set_ylabel("seconds (local, 10 cores)"); ax[0].legend(fontsize=7)
    for w, pts in cores.items():
        xs = sorted(pts); ax[1].plot(xs, [pts[1] / pts[x] for x in xs], marker="o", label=w)
    ax[1].plot([1, 10], [1, 10], "k:", lw=0.7, label="ideal")
    ax[1].set_xlabel("cores (local[k], 36.1M rows)"); ax[1].set_ylabel("speed-up vs 1 core"); ax[1].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(figs / "scalability.png", dpi=150)
    lines = ["| Workload | Rows | Cores | Seconds | Rows/s | Shuffle write MB | Master |", "|---|---:|---:|---:|---:|---:|---|"]
    for r in runs:
        lines.append(f"| {r['workload']} | {r['rows_in']:,} | {r['cores']} | {r['seconds']:.1f} | {r['rows_per_s']:,.0f} | "
                     f"{r['shuffle_write_bytes']/1e6:.0f} | {r['master']} (sp={r['shuffle_partitions']}, aqe={r['aqe']}) |")
    Path("paper/tables/scalability.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"size": size, "cores": cores}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
