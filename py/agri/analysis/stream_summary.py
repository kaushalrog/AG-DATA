"""Summarise a streaming run from results/streaming/*.jsonl into demo_summary.json."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

R = Path("results/streaming")


def main(root: str = "data/stream") -> int:
    batches = [json.loads(l) for l in (R / "batches.jsonl").read_text().splitlines() if l.strip()] if (R / "batches.jsonl").exists() else []
    progress = [json.loads(l) for l in (R / "progress.jsonl").read_text().splitlines() if l.strip()] if (R / "progress.jsonl").exists() else []
    silver = [p for p in progress if p.get("name") == "silver" and p.get("numInputRows", 0) > 0]
    rates = [p.get("processedRowsPerSecond", 0) for p in silver]
    # numInputRows of the quarantine query counts SOURCE rows (before its filter); count the sink instead
    qdir = Path(root) / "quarantine" / "prices"
    quarantined = None
    if qdir.exists():
        import duckdb
        quarantined = duckdb.connect().execute(
            f"SELECT count(*) FROM read_parquet('{qdir}/*/*.parquet', hive_partitioning=true)").fetchone()[0]
    dropped_wm = sum(op.get("numRowsDroppedByWatermark", 0) for p in progress if p.get("name") == "silver"
                     for op in p.get("stateOperators", []))
    dedup_removed = sum(op.get("numDroppedDuplicateRows", 0) for p in progress if p.get("name") == "silver"
                        for op in p.get("stateOperators", []) for op in [op.get("customMetrics", op)])
    behind = [float(s["metrics"].get("avgOffsetsBehindLatest", "nan")) for p in silver for s in p.get("sources", [])
              if s.get("metrics", {}).get("avgOffsetsBehindLatest") is not None]
    p50 = [b["latency_producer_to_sink_p50_s"] for b in batches if b.get("latency_producer_to_sink_p50_s") is not None]
    p95 = [b["latency_producer_to_sink_p95_s"] for b in batches if b.get("latency_producer_to_sink_p95_s") is not None]
    out = {
        "data_origin": sorted({o for b in batches for o in b.get("data_origin", [])}),
        "micro_batches_with_data": len(batches),
        "rows_silver": sum(b["rows_silver"] for b in batches),
        "rows_quarantined": quarantined,
        "rows_dropped_by_watermark": dropped_wm,
        "duplicate_rows_removed": dedup_removed,
        "silver_input_rows": sum(p.get("numInputRows", 0) for p in silver),
        "alerts": sum(b["alerts"] for b in batches),
        "latency_producer_to_sink_p50_s_median_over_batches": float(np.median(p50)) if p50 else None,
        "latency_producer_to_sink_p95_s_max_over_batches": float(np.max(p95)) if p95 else None,
        "processed_rows_per_s_median": float(np.median(rates)) if rates else None,
        "processed_rows_per_s_max": float(np.max(rates)) if rates else None,
        "avg_offsets_behind_latest_max": float(np.nanmax(behind)) if behind else None,
        "producer": json.loads((R / "producer_summary.json").read_text()) if (R / "producer_summary.json").exists() else None,
        "parity": json.loads((R / "parity.json").read_text()) if (R / "parity.json").exists() else None,
        "parity_note": "records_streamed counts original replay events only; where a labelled duplicate/late copy won "
                       "de-duplication, that event is excluded from the column comparison (it is still in the id comparison).",
        "note": "Replay of archived real reports through a local single-broker Kafka and local-mode Spark; not a live source, not a cluster.",
    }
    (R / "demo_summary.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
