# Architecture

AG-DATA 2.0 turns published mandi price reports into evaluated price forecasts, uncertainty ranges, anomaly alerts and cautious decision cards. These outputs reach farmers through an installable, six-language web app. This document explains the job of each component. Measured behaviour is in `docs/EXPERIMENTS.md`. Every limitation is in `docs/KNOWN_LIMITATIONS.md`.

```
 Official sources                     Ingestion (py/agri/ingest)            Streaming (Scala)
 ───────────────                      ──────────────────────────            ─────────────────
 data.gov.in OGD API  ──(key)──▶ DataGovInClient ─┐                      ┌▶ BRONZE  raw JSON + offsets  (replay source of truth)
 (AGMARKNET daily)               retry/backoff,   │   Kafka              │
                                 rate limit,      ├──▶ agri.prices.v1 ───┤  PriceEventStream
 Archived AGMARKNET   ─────────▶ ArchiveReplay ───┘   6 partitions,      │   parse → schema check → standardize (shared)
 (2001-2026 snapshot)            (data_origin=replay)  key=business key  │   → watermark 10 d → drop re-sends by event_id
                                                                         └▶ SILVER (stream) ─▶ ALERTS (vs batch entity stats)
                                                                              │ quarantine for invalid messages
 Batch (Scala/Spark)                                                          ▼
 ───────────────────                                                    reconciled by batch backfill
 raw CSV ─▶ Readers ─▶ DataQuality ─▶ Deduplicate ─▶ SILVER (Parquet, year=)
                                                      │
                                                      ▼
                         BuildForecastFeatures: harmonise ids → causal sanity rule → panel eligibility (2021-23)
                                                → window features (≤ t) → targets (> t) → FEATURES (year=)
                                                      │
                         ForecastBenchmark: baselines + MLlib LR/RF/GBT → tune on 2024 → conformal on 2024
                                                → score 2025-26 once → METRICS, MODELS, PREDICTIONS, registry
                                                      │
                         ForecastPublish: apply selected models to latest reports → GOLD (small Parquet + meta.json)
                                                      │
 API (FastAPI + DuckDB, read-only) ◀──────────────────┘   /api/v1/*  typed JSON, codes not prose, rate limit, CORS
        │
        ▼
 PWA (app/): vanilla JS, 6 languages, service worker, offline cache, demo snapshot, SELL/HOLD/WATCH/COMPARE
```

## Why each piece exists

| Component | Purpose | Why not something simpler / heavier |
|---|---|---|
| Scala + Spark DataFrames | Window features over 33M reports and 117k series; 76M-row profiling and deduplication | Pandas cannot hold the data on a 16 GB laptop. The same jobs run unchanged with `--master spark://…` and `hdfs://` paths |
| Spark MLlib (LR, RF, GBT) | Global models trained on 2M sampled rows, persisted as `PipelineModel` and applied in `ForecastPublish` with no other runtime | No GPU is needed for tabular gradient boosting at this size. A deep model would need a separate serving stack, and the literature does not show it beats strong baselines on this target (see RESEARCH_GAP) |
| Parquet layers (bronze/silver/features/gold) | Columnar, compressed and replayable. Each layer is rebuilt from the one before | Parquet replaced row-cached Spark frames after a run filled the disk (see EXPERIMENTS § incidents) |
| HDFS (1 NameNode + 3 DataNodes, Docker) | Shared, replicated data lake for a cluster deployment. Replication 3 is demonstrable | Local disk is used for development. The jobs take `AGRI_*` path variables. **No NameNode HA**: a single NameNode is a single point of failure |
| Kafka + Structured Streaming | Incremental path for daily reports: bounded micro-batches, checkpointed offsets, de-duplication within a watermark | Historical bulk data is **not** pushed through Kafka. Batch reads the files directly |
| FastAPI + DuckDB | Serves the small gold tables (about 100k rows) in milliseconds, read-only, with no Spark at request time | A JVM/Spark server per request would be wasteful. Mobile requests never trigger training |
| PWA (no framework) | Installable, offline, about 80 KB of JS, works on low-end Android over slow networks | A native app would need store distribution. A framework would add size without adding function |

## Batch and streaming consistency

The two paths share code, not just conventions:

* **Canonicalisation, quality rules and entity id:** `CanonicalEvent.standardize` and `Features.entityIdCol` are used by batch (`batchToCanonical`), streaming (`eventsToCanonical`) and parity checks. `StreamingSpec` pushes the same records through both entry points and requires identical rows. `StreamParityCheck` repeats the comparison on real replayed records (`results/streaming/parity.json`).
* **Units and time:** INR/quintal on both paths. Event time is `arrival_date`; ingestion time (`ingest_ts`) and broker time are kept separately.
* **Anomaly rule:** `Anomaly.withScore` is used by `ForecastPublish` (batch alerts) and `PriceEventStream` (streaming alerts). Both score a report against trailing statistics that exclude it.
* **Features and forecasts are computed in batch only.** Streaming does not maintain rolling features. Forecasts are recomputed by the daily batch run (`ForecastPublish`), so the only streaming output is validated reports and alerts. This was a deliberate trade-off: one feature implementation instead of two that could drift apart.

### Late, duplicate and corrected reports
* **Exact re-sends** have the same content hash (`event_id`) and are dropped within the 10-day watermark. The producer is also idempotent within a session (`enable.idempotence=true`, `acks=all`).
* **Corrections** (same key, new price) get a new `event_id` and are kept. The batch layer resolves them by keeping the latest ingested version when silver is rebuilt.
* **Out-of-order events** within the watermark are processed normally.
* **Events older than the watermark** are kept in bronze but dropped from streaming silver, and counted as `numRowsDroppedByWatermark` in `results/streaming/progress.jsonl`. Reconciling them requires the batch backfill below, which is a **manual procedure, not an automated job** (KNOWN_LIMITATIONS #25).
* **Unusable messages** are routed to a separate quarantine query **before** the watermark. These are malformed JSON, unknown `schema_version`, or a missing date. They therefore never influence event time: red-team RT-01 found that an earlier version let one malformed message advance the watermark and drop all later events.

### Delivery guarantees, stated precisely
* **Kafka to bronze/silver sinks:** Structured Streaming records offset ranges in its checkpoint before committing. The file sink (bronze) commits through `_spark_metadata`. The silver `foreachBatch` sink overwrites `batch_id=N`, so a re-executed micro-batch rewrites the same output. Together this gives **effectively-once output per offset range**.
* **Producer to Kafka:** idempotent within one producer session. Duplicates created across sessions or by the source are removed by `event_id` within the watermark.
* **Not claimed:** end-to-end exactly-once from the government source to the app. The source has no stable record ids, and the API reads a gold snapshot produced by batch.

## Replay and backfill procedure
1. **Stop** the streaming query. Its checkpoint keeps the committed offsets.
2. **Reprocess a time range from bronze.** Read `bronze/prices_raw` for the affected `ingest_date`s, de-duplicate by `event_id`, and rebuild silver from it. Alternatively, restart from earliest offsets with a fresh checkpoint directory while Kafka still retains the data (retention 14 days).
3. **Rebuild downstream layers.** Rebuild silver (batch), then rerun `BuildForecastFeatures` and `ForecastPublish`. Features and forecasts are pure functions of silver, so a backfill is a rerun.
4. **Recover from a crash** by restarting with the same `checkpointLocation`. `StreamingSpec` tests that committed events are not reprocessed and that de-duplication state survives a restart.

## HDFS layout

| Path | Contents | Partitioning | Retention / owner |
|---|---|---|---|
| `/agri/raw/` | source CSVs | as downloaded | permanent / ingestion |
| `/agri/bronze/prices_raw` | Kafka records as received | `ingest_date=` | 90 days / streaming |
| `/agri/silver/daily_market_prices` | canonical batch layer | `year=` (26 dirs, no small-file explosion) | permanent / batch |
| `/agri/silver/prices_stream` | canonical streaming layer | `batch_id=` (compacted by batch backfill) | until backfilled |
| `/agri/features/forecasting` | feature table | `year=` | rebuilt per run |
| `/agri/models/<exp>/<h>/<family>` | MLlib pipelines | per experiment | keep selected + last 3 |
| `/agri/predictions/<exp>` | test predictions | `horizon=` | per experiment |
| `/agri/gold/` | serving tables | none (small) | overwritten per publish |
| `/agri/checkpoints/` | streaming checkpoints | per query | permanent while query exists |
| `/agri/metadata/` | manifests, registry | — | permanent |

**Four kinds of partitioning, often confused:**
* *HDFS block size* (128 MB) is the unit of storage and replication.
* *Spark input partitions* are roughly one task per block or Parquet row group.
* *`spark.sql.shuffle.partitions`* (64 here, then coalesced by AQE) is the parallelism after a shuffle.
* *Output directory partitioning* (`year=`) is for pruning. It uses low-cardinality columns only. Partitioning by market or entity would create about 100k directories of tiny files.

## Security boundaries
Only the API port (and the static app it serves) is meant to be public. The HDFS ports (9870, 9000), Kafka (9092) and the Spark UI must stay on a private network. `docker-compose.yml` publishes them to localhost for development only. Details are in `docs/SECURITY.md`.
