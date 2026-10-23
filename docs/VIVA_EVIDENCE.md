# Viva Evidence Guide

> Corrected 2026-10-23: figures now come from docs/VERIFIED_METRICS.md; original wording preserved in Git commit 3926155.

This document maps core concepts to their concrete usage within the **AG-DATA 2.0 mandi price forecasting and farmer decision support** project, serving as direct evidence for viva/project defense. Every number below is taken from `docs/VERIFIED_METRICS.md` (the section is given in brackets).

## Data Scale and Volume
- **Raw archive:** 75,984,017 rows (Kaggle mirror of AGMARKNET daily prices, v134) [§1].
- **Archive silver layer** (after quality rules and de-duplication): 75,644,801 rows [§1].
- **Silver v2** (archive before 2025-10-01 + official data.gov.in from 2025-10-01): 82,114,083 rows [§1].
- **Official back-fill:** 7,720,662 records over 387 days (2025-10-01 → 2026-10-22), 0 failed days [§1]. The archive mirror holds only 30.0% of official reports for 2025-10-01 → 2026-04-21 [§1].
- **Forecast panel:** 36 commodities, 11,845 series, 21.06 M feature rows [§1].
- **Synthetic workload:** a synthetic workload from v1 exists (labelled `synthetic_scaled`) for scalability tests only. It was not re-run for AG-DATA 2.0 and is never used for any model.

## HDFS (Distributed Storage)
- **1 NameNode** → manages metadata and namespace.
- **3 DataNodes** → store the blocks (Docker, one host).
- **Replication factor 3** → silver layer (692 MB) loaded with replication 3, status HEALTHY, and readable with one DataNode down [§5]. All three DataNodes share one physical disk, so this demonstrates HDFS behaviour, not hardware durability.
- **Layout:** `/agri/{raw,bronze,silver,features,models,predictions,gold,checkpoints,metadata}` (`docs/ARCHITECTURE.md`).

## Spark (Distributed Processing)
- **DataFrames / SQL** → readers, quality rules, de-duplication, and the forecast panel.
- **Window Functions** → leakage-safe features: every feature window ends at the current report or earlier; every target starts strictly after it (`forecast/Features.scala`, tested by `ForecastFeaturesSpec`).
- **Structured Streaming** → `PriceEventStream` reads Kafka, writes bronze (raw + offsets), quarantines invalid messages before the 10-day watermark, de-duplicates re-sends by `event_id`, and writes silver and alerts.
- **Scaling:** Docker Spark cluster (2 workers × 3 cores, one host) on 11.27 M rows: W1 aggregate 9.2 s, W2 window features 14.4 s. Local (Apple M5, 10 cores) on the full 75.6 M rows: W1 42.2 s, W2 65.9 s; speed-up at 10 cores 2.4× (W1) and 3.0× (W2) [§5].

## Kafka (Event Transport)
- **Transport Mechanism** → topic `agri.prices.v1` (6 partitions, key = business key) decouples ingestion from processing; it is not a database.
- **Replay demo:** 21,524 messages = 20,000 to silver + 1,317 duplicates removed + 207 quarantined; 0 missing; batch/stream parity 0 mismatches; producer→sink p50 latency 1.69 s [§5].
- **Live check (2026-10-23):** 4/4 current-day records went through Kafka to silver [§5].
- **Delivery semantics:** effectively-once output per offset range. End-to-end exactly-once from the government source to the app is **not** claimed (`docs/ARCHITECTURE.md`).

## MLlib (Machine Learning): price forecasting
- **Task:** forecast the modal price a mandi will report next / in 3 / 7 / 14 days, with 80% conformal intervals [§2].
- **Splits:** train origins 2016–2023, validation 2024, test 2025-01-01 → 2026-04-20, scored once [§2].
- **Selected models:** next and 3 days: GBT with absolute loss on a percent target (depth 7, 150 iterations, step 0.5); 7 and 14 days: random forest (60 trees, depth 10) [§2].
- **Test results (relative MAE vs persistence, lower is better):** next 0.971, 3 d 0.953, 7 d 0.938, 14 d 0.923; Diebold–Mariano p from 3.6e-47 to 1.3e-22; 80% interval coverage 78.6–80.5% [§2].
- **Frozen models on new data (no refitting):** prospective 2026-04-22 → 2026-10-22: 0.963 / 0.955 / 0.958 / 0.952, coverage 76.9–80.1% [§2].
- **Viva Defense Point on Metrics** → Persistence ("last price") is a hard baseline: 17–34% of target changes are exactly zero [§1]. The gains are modest (about 3–8%) but statistically significant, hold on 58.5–76.4% of individual series, and survive six months of unseen data.

## Anomaly flags
- Evaluated **only on injected, labelled corruptions**: production rule (trailing robust z) PR-AUC 0.704 vs 0.352 for the legacy commodity IQR rule; precision 0.313, recall 0.846, FPR 0.019 [§3].
- **No accuracy figure for real anomalies exists**, because there are no labels for real anomalies [§3].

## What changed and why (v1 anomaly classifier withdrawn)
The v1 version of this guide quoted a Random Forest anomaly classifier with very high accuracy, precision, recall and F1 on a "2025+ test set". Those figures were not produced by any code or log in the repository and have been **withdrawn** (see `docs/AUDIT_PRIOR_RESULTS.md` and VERIFIED_METRICS §6). The v1 labels were functions of the features, and its outlier bounds were fitted on all years including the test period, so the v1 classifier was also not leakage-free. The only logged v1 figure (next-observation classifier, 72.54% accuracy) is below its 84.35% all-normal baseline. AG-DATA 2.0 replaced the classifier with the forecasting benchmark above.

## Dashboard Visualization
- **PWA (`app/`)** served by FastAPI + DuckDB (read-only gold tables): six languages, offline cache, SELL / HOLD / WATCH / COMPARE decision cards. On the 7-day test: WATCH on 98.5% of report-days, HOLD on 0.5% (hit rate 80.0%), SELL on 1.0% (hit rate 67.8%) [§2]. These are hit rates on published prices, not farm profits.
- **Streamlit (`src/dashboard/app.py`)** → legacy v1 dashboard, now showing the verified figures.

## Tests
- Scala 21, Python 62 (59 + 3 skipped in CI without data), app 56 [§5].

*(Note: Apache Hadoop YARN and MapReduce are NOT used for execution; Spark runs in `local[*]` mode or on a small Docker standalone cluster on one host.)*
