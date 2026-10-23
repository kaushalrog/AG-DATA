# Experiments: protocol, reproduction and results

The protocol in Part A was fixed in code (`ForecastConfig.scala`, `ForecastBenchmark.scala`) before the test period was scored. Part B records the results. Every number in Part B is copied from a file under `results/`, and the file is named next to it.

## Part A: protocol

### A.1 Data
* **Source:** the archived AGMARKNET daily price reports (Kaggle `khandelwalmanas/daily-commodity-prices-india` v134, GODL-India; provenance in `docs/DATA_SOURCES.md`). After quality classification and business-key de-duplication (silver layer) this is 75,644,801 rows covering 2001-01-10..2026-04-21.
* **Scope:** the 36 commodities listed in `conf/forecast_commodities.txt`, reports from 2014-10-01 onward (earlier history only warms up the lags). The list was built from training-period data in four steps:
  1. take an a-priori list of staple crop-name patterns;
  2. keep matches with more than 50k VALID reports in 2021–23;
  3. drop two duplicate or processed forms;
  4. keep the 36 with the most reports.

  The full rule is in the file header. It is not "the overall top 36".
* **Cleaning, in order:**
  * quality flag must be `VALID`;
  * identifier harmonisation: grade is not part of the key, and the " APMC" suffix is removed;
  * the causal ×5 sanity rule.

  Counts for each step are in `results/forecast/panel_report.json`.
* **Panel:** an entity is eligible if it has at least 300 distinct report days in 2021-01-01..2023-12-31, so eligibility is decided from training-period data only. Non-panel entities still get features and live forecasts. They are excluded from training and from headline metrics.

### A.2 Forecasting task
For each report at origin t the task is to predict the modal price at horizon h:
* **next**: the next report, if it falls within 7 days;
* **h3, h7, h14**: the first report dated in [t+h, t+h+3]. If there is no report in that window, there is no label. Mandis do not report every day, so this is the calendar definition of "an h-day forecast".

All models predict y = ln P(target) − ln P(t). Errors are measured in rupees on P(t)·exp(ŷ).

### A.3 Splits (chronological, purged)
| Period | Origins | Target constraint | Use |
|---|---|---|---|
| Train | 2016-01-01..2023-12-31 | target date ≤ 2023-12-31 | fitting; MASE scale |
| Validation | 2024-01-01..2024-12-31 | target date ≤ 2024-12-31 | hyper-parameter and model choice; conformal calibration |
| Test | 2025-01-01..2026-04-21 | the data end | scored once |

The StringIndexer, StandardScaler and conformal quantiles are all fitted on train or validation rows only. Training rows are a uniform random sample (seed 20261022) of at most 2,000,000 rows per horizon. Tuning uses a random sample of at most 600,000 validation rows.

**Rolling origin (stability):** `ForecastBacktest` refits the chosen GBT configuration on an expanding window, with test years 2021, 2022, 2023 and 2024.

### A.4 Candidates
* **Baselines:**
  * persistence (ŷ = 0);
  * geometric moving average of the last 7 and 30 days;
  * seasonal naive (last year's level near t+h; falls back to persistence when absent, and the fallback rate is reported);
  * seasonal-adjusted persistence (today's level × last year's change over the same horizon).
* **Spark MLlib (search space v3, 8 fits per horizon):**
  * ridge regression, regParam ∈ {1e-4, 1e-2}, with standardised features and one-hot commodity;
  * Huber regression (regParam 1e-4);
  * random forest (60 trees, depth 10);
  * squared-loss GBT (depth 6, 200 iterations, step 0.05);
  * absolute-loss GBT on the percent target: (depth 5, 150, 0.5), (depth 7, 150, 0.5), (depth 6, 300, 0.25).

  The original v1 space is described in A.10.

  All candidates use 24 base features, one horizon-specific seasonal feature and the commodity index (listed in `docs/DATA_DICTIONARY.md`).
* **Selection:** the candidate with the lowest validation MAE in rupees, with baselines included in the comparison. If nothing beats persistence on validation, persistence is selected.

### A.5 Metrics
MAE, RMSE, WAPE, sMAPE, bias, MASE (scale: the entity's in-sample h-step naive MAE on training rows), MAE relative to persistence on the same rows, and directional accuracy (rows with |y| ≥ 1%). Definitions are in `ForecastEval.scala`. MAPE is not used: near-zero prices of leafy vegetables make it unstable.

**Significance:** Diebold–Mariano tests on daily mean absolute-error differentials against persistence. They use a Newey–West variance with lag = h and the HLN correction (`py/agri/analysis/forecast_report.py`). Errors are averaged per date first, because same-day errors across markets are correlated.

**Intervals:** split-conformal, Mondrian over five volatility (std30) buckets, at 80% and 90%. Empirical test coverage and mean relative width are reported overall and per bucket.

### A.6 Decision-support backtest
Using the selected model's 80% interval on the test period, with costs from `conf/decision_rules.json`:
* **HOLD** if lo80 ≥ ln(1 + cost_h);
* **SELL** if hi80 ≤ 0;
* **WATCH** otherwise.

Hit rates: HOLD is correct when the realised return is at least the cost; SELL is correct when the realised return is below 0.

### A.7 Anomaly detection
Corruptions are injected into real 2025 series and labelled:
* data errors: ×10, ×100 or ÷10;
* shocks: ±35–60% moves.

The production trailing-z rule is compared with a previous-change baseline and the legacy commodity-IQR rule. Metrics are PR-AUC, precision, recall, F1 and FPR (`py/agri/analysis/anomaly_benchmark.py`). There are no labels for real anomalies, so no accuracy is claimed for them.

### A.8 Budget
On the development machine (Apple M-series, 10 cores, 16 GB RAM, local Spark 4.2.0, Java 21):
* the search space is deliberately small (8 fits per horizon; the final run took 1 h 41 min) to stay within the compute budget;
* no GPU is used: the models are tabular, MLlib has no GPU path, and the data fits CPU training. See ARCHITECTURE for the rationale.

### A.10 Protocol amendment (2026-10-22, before any test metric was read)
The first run (`logs/f2_benchmark_fc_main_v1_ABORTED_searchspace_v1.log`) used squared-loss models only. On validation at the next-report horizon, persistence was selected: its MAE of ₹211.20 tied the best model, RF, at ₹211.14 on the tuning sample. The cause is measured on 2024 validation rows. The share of target changes that are exactly zero is:

| next | h3 | h7 | h14 |
|---:|---:|---:|---:|
| 34.4% | 27.9% | 21.8% | 17.2% |

Mandis often re-quote an unchanged modal price. A squared loss estimates the conditional mean, while MAE, the selection and headline metric, is minimised by the conditional median. The median is frequently exactly "no change".

**Second amendment (v3), also from validation only.** In run v2 (`logs/f2_benchmark_fc_main_v2_ABORTED_l1_unscaled.log`) the absolute-loss GBTs scored a validation MAE of ₹271–276, against ₹211 for persistence. The cause is MLlib's implementation. After the first tree, each tree is fitted to sign(residual) ∈ {−1, +1} without a leaf line search, so each iteration moves the prediction by up to `stepSize`. At 0.1 log units that is about ten times the typical change. In v3 the absolute-loss GBTs are trained on the target in percent (×100) with `stepSize` 0.25–0.5, so each step is at most 0.0025–0.005 log units. The prediction is rescaled inside the persisted pipeline. `ForecastEvalSpec` checks that this model recovers the conditional median of a zero-inflated target, where squared loss recovers the mean, and that the reloaded model predicts unlabelled rows. Ablations were restricted to the 7-day horizon to fit the compute budget.

The search space was therefore extended (v2) with:
* absolute-loss GBT in three configurations (v3: depth 5 / 150 iterations / step 0.5, depth 7 / 150 / 0.5, depth 6 / 300 / 0.25, percent target);
* Huber-loss ridge regression.

Only the GBT(6, 200, 0.05) squared-loss configuration was kept from v1, as the strongest of the v1 GBTs on validation.

**Disclosure (red-team RT-07).** Run v1 was not stopped before it touched the test period. On the first horizon (`next`) it had already computed test metrics in memory and written `test_by_commodity_next.csv` and the test predictions when it crashed, during the per-state breakdown. Those files were deleted without being opened, and the console log shows validation numbers only. The amendment rests on validation evidence alone, but a reader should know the test period had been scored once by v1. Part B reports, as a sensitivity row, what the v1 search space would have selected. A `DIVIDE_BY_ZERO` failure in the same run was fixed: Spark 4's ANSI mode raised it on directional accuracy for groups with no move of 1% or more.

### A.9 Reproduce
```bash
source scripts/env.sh
sbt "runMain com.agribigdata.preprocessing.PreprocessDatasets"     # silver layer (once)
scripts/run_forecast_pipeline.sh                                    # F1 → F2 → backtest → report → publish
.venv/bin/python -m agri.analysis.anomaly_benchmark
scripts/streaming_demo.sh 20000 2000
scripts/hdfs_verify.sh
```
Every run appends a manifest line to `results/experiments/registry.jsonl` with these fields:
* experiment id, git commit and dirty flag;
* Spark and Java versions, master URL;
* periods, sizes, search space, seed;
* selected models, warnings, and the paths of models and predictions.

---

## Part B: results (experiment `fc_main_v3`)

Source files: `results/forecast/fc_main_v3/` (manifest, tuning, metrics_overall, intervals, decisions, ablation, test_by_*, test_daily_loss_*, dm_tests, test_subperiods, test_series_wins, decisions_robust). The tables in `paper/tables/` are generated from these files by `py/agri/analysis/forecast_report.py`.

Run: 2026-10-23, local[*] (10 cores), Spark 4.2.0, Java 21.0.12, wall time 1 h 41 min, git dirty (uncommitted work), seed 20261022.

### B.1 Data sizes
| Horizon | Train rows (sampled) | Validation rows | Test rows |
|---|---:|---:|---:|
| next | 15,651,010 (2,000,225) | 2,062,412 | 1,674,682 |
| h3 / h7 / h14 | 15–16 M (2.0 M) | ~2.06 M | 1,597,768 / 1,580,395 / 1,546,914 |

### B.2 Validation (model choice)
Validation MAE (₹/quintal) on 600k sampled 2024 rows, from `tuning.csv`:

| Horizon | Persistence | Best squared-loss model | Best Huber | Best absolute-loss GBT | Selected |
|---|---:|---:|---:|---:|---|
| next | 210.74 | RF 211.14 | 212.53 | 205.29 | GBT-L1 (d7) |
| h3 | 277.52 | RF 267.19 | 275.07 | 266.16 | GBT-L1 (d7) |
| h7 | 363.62 | RF 342.32 | 356.14 | 344.82 | RF |
| h14 | 476.16 | RF 444.13 | 468.73 | 454.26 | RF |

Selection uses the full validation set; the sampled numbers above were used for tuning within each family.

**v1 sensitivity (RT-07).** With only the v1 squared-loss space, validation would have selected:
* **next:** persistence (210.74 < 211.14), giving test relative MAE 1.000 instead of 0.971;
* **h3:** RF, giving test relative MAE 0.958 instead of 0.953;
* **h7, h14:** RF, the same as now.

### B.3 Test results (2025-01-01 .. 2026-04-21, scored once)
Full table: `paper/tables/main_results.md`. Headline rows:

| Horizon | Persistence MAE | Selected MAE | Rel. MAE | Selected MASE | WAPE % | DM stat (HLN) | p | Series where selected wins |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| next | 189.0 | 183.5 | **0.971** | 1.559 | 5.56 | −10.3 | 1e-22 | 58.5% of 8,719 |
| h3 | 242.6 | 231.1 | **0.953** | 1.680 | 7.02 | −16.3 | 4e-47 | 68.8% of 8,603 |
| h7 | 308.8 | 289.7 | **0.938** | 1.430 | 8.80 | −14.5 | 4e-39 | 75.0% of 8,568 |
| h14 | 397.0 | 366.4 | **0.923** | 1.056 | 11.14 | −12.0 | 9e-29 | 76.4% of 8,537 |

* **Gains are modest (3–8% lower MAE) but consistent.** They are significant at every horizon, they grow with the horizon, and at h7 they hold for all 36 commodities: relative MAE runs from 0.879 (Jowar) to 0.969 (Banana).
* **Persistence MASE > 1 in the test period** at short horizons (1.52 for next). Test-period changes are larger than the training-period naive errors used to scale MASE, so MASE values are not centred on 1 for persistence.
* **Seasonal naive is the worst baseline** (relative MAE 2.5–5.1, bias +395 to +433 ₹/q). Year-over-year level shifts dominate any seasonal pattern at this granularity. Seasonal-adjusted persistence is also worse than persistence (1.10–1.34).
* **Moving averages lose to persistence** at short horizons.
* **The squared-loss ridge regression does not beat persistence at next** (1.002, DM p = 0.47). RF only ties it (0.997, p = 0.28). The absolute-loss GBT does beat it (0.971).

### B.3a Per-series statistical baseline (SES), on a random sample of 400 panel series
`results/forecast/fc_main_v3/stat_baseline_ses.json` (`py/agri/analysis/stat_baseline.py`). Simple exponential smoothing on the log price, with α fitted per series on 2016–2023 origins only, compared on exactly the same test rows:

| Horizon | Test rows | Rel. MAE SES | Rel. MAE selected global model | Mean α |
|---|---:|---:|---:|---:|
| next | 69,123 | 0.975 | 0.976 | 0.83 |
| h3 | 65,774 | 0.962 | 0.960 | 0.77 |
| h7 | 65,099 | 0.967 | **0.946** | 0.72 |
| h14 | 63,612 | 0.975 | **0.935** | 0.68 |

A per-series smoother is as good as the global MLlib model at 1–3 days. The learned model adds value at 7–14 days, where cross-market and seasonal information matter. Any claim that ML helps at the shortest horizons must be made against SES, not only against persistence.

### B.4 Sub-periods (AGMARKNET 2.0 migration)
`paper/tables/subperiods.md`:

| Horizon | Rel. MAE 2025-01..10 | Rel. MAE 2025-11..2026-04 | 80% coverage before | after |
|---|---:|---:|---:|---:|
| next | 0.970 | 0.993 | 79.2% | 67.6% |
| h3 | 0.951 | 0.977 | 79.7% | 71.3% |
| h7 | 0.937 | 0.968 | 80.3% | 72.0% |
| h14 | 0.922 | 0.944 | 80.9% | 72.9% |

After the migration, accuracy gains shrink and the intervals under-cover by 7–12 points: a measured distribution shift.

### B.5 Prediction intervals
`intervals.csv`. Overall test coverage of the nominal 80% / 90% intervals:

| Horizon | 80% coverage | 90% coverage | Mean relative width (80%) |
|---|---:|---:|---:|
| next | 78.6% | 88.9% | 0.21 |
| h3 | 79.4% | 89.5% | 0.26 |
| h7 | 80.0% | 90.0% | 0.33 |
| h14 | 80.5% | 90.5% | 0.44 |

* Coverage per volatility quintile ranges from 77.2% (lowest-volatility quintile, h14) to 82.0%.
* Interval width grows from 2–8% of the price in the calmest quintile to 45–88% in the most volatile.

### B.6 Decision-support backtest (HOLD/SELL on 80% intervals)
`decisions.csv`, `decisions_robust.json`:

| Horizon | HOLD share | HOLD hit rate | HOLD median realised return | SELL share | SELL hit rate | WATCH share |
|---|---:|---:|---:|---:|---:|---:|
| h3 | 1.0% | 76.6% | +20.0% | 1.2% | 72.0% | 97.8% |
| h7 | 0.5% | 80.0% | +46.8% | 1.0% | 67.8% | 98.5% |
| h14 | 0.5% | 73.4% | +41.5% | 0.9% | 70.8% | 98.5% |

* **Conservative by design.** The rule abstains (WATCH) on about 98% of report-days.
* **HOLD concentrates on reports far below the series' recent level**, where prices revert. This explains the large median returns and matches `dev7` being the most important RF feature. Some of these low reports may be reporting errors smaller than the ×5 sanity threshold.
* These are hit rates on published modal prices, **not farm-gate profits**.
* COMPARE is not back-tested.

### B.7 Ablation (h7, best GBT configuration)
`ablation.csv`, test relative MAE:

| Variant | Rel. MAE |
|---|---:|
| full | 0.944 |
| no calendar | 0.947 |
| no level | 0.948 |
| no seasonal | 0.947 |
| **no cross-section** | **0.960** |
| returns only (3 features) | 0.970 |

* The same-day cross-market features (`cs_*`, `sc_*`) are the only group whose removal clearly hurts.
* Their availability at the origin is an assumption (KNOWN_LIMITATIONS #24).
* RF feature importance at h7, top 4: dev7 0.18, ret1 0.12, cs_dev30 0.10, sc_dev30 0.09.

### B.8 Anomaly detection (injected corruptions; run `results/anomaly/20261022T175225Z`)
400,000 real 2025 rows, 1% corrupted (2,000 unit or keying errors, 2,000 shocks).

| Target | Detector | PR-AUC | Precision | Recall | FPR |
|---|---|---:|---:|---:|---:|
| any | **production rule** | **0.704** | 0.313 | 0.846 | 0.019 |
| any | trailing z only | 0.695 | 0.258 | 0.845 | 0.025 |
| any | previous-report change | 0.671 | 0.160 | 0.960 | 0.051 |
| any | legacy commodity IQR | 0.352 | 0.208 | 0.371 | 0.014 |
| data errors | production rule | 0.897 | 0.212 | 0.999 | 0.019 |
| data errors | previous-report change | **0.996** | 0.090 | 1.000 | 0.051 |
| shocks (±35–60%) | production rule | 0.252 | 0.157 | 0.692 | 0.019 |

* The production rule flags 1.87% of uncorrupted rows. Some of these may be genuine market events; without labels this cannot be resolved.
* For pure data-error detection, the previous-report change ranks better.
* Abrupt shocks are hard for every detector.

## Part C: stability, streaming and platform evidence

### C.1 Rolling-origin backtest
Files: `results/forecast/fc_main_v3/backtest_gbt_d7_i150_s0.5_absolute.csv` (next, h3) and `backtest_rf_t60_d10.csv` (h7, h14). The selected configuration per horizon is refitted on an expanding window, origins from 2016-01-01 to the end of year Y−1, and tested on year Y.

| Horizon | 2021 | 2022 | 2023 | 2024 | main test 2025–26 |
|---|---:|---:|---:|---:|---:|
| next (GBT-L1) | 0.974 | 0.970 | 0.970 | 0.976 | 0.971 |
| h3 (GBT-L1) | 0.956 | 0.953 | 0.952 | 0.960 | 0.953 |
| h7 (RF) | 0.946 | 0.940 | 0.936 | 0.943 | 0.938 |
| h14 (RF) | 0.936 | 0.921 | 0.920 | 0.933 | 0.923 |

Values are MAE relative to persistence. The improvement is stable across five test years.

Caveats:
* The 2024 fold is the validation year on which the configurations were chosen.
* For the 2021–2023 folds, panel membership used 2021–23 reporting density. This is a selection effect only; no prices or labels are involved.

### C.2 Streaming (Kafka 4.3.1 single broker, KRaft; Spark 4.2 local[*])
Run with `scripts/streaming_demo.sh 20000 2000`. Results are in `results/streaming/` (`demo_summary.json`, `parity.json`, `progress.jsonl`, `batches.jsonl`, `producer_summary.json`).

The workload was 20,000 **real archived reports** (2026-04-15..21) replayed at 2,000 events/s, with labelled faults:
* 5% duplicates;
* 2% late re-sends appended at the end;
* 1% invalid messages;
* shuffling within windows of 50.

| Quantity | Value |
|---|---:|
| Messages produced (idempotent producer, acks=all) | 21,524, 0 delivery errors |
| Valid distinct events sent | 20,000 |
| Distinct events in streaming silver | **20,000** (0 missing, 0 never sent) |
| Duplicate or late copies removed by `dropDuplicatesWithinWatermark` | 1,317 |
| Quarantined (malformed, before the watermark) | 207 |
| Dropped by the watermark | 0 |
| Accounting | 21,524 = 20,000 + 1,317 + 207 |
| Batch/stream canonicalisation parity (14 columns, 19,536 original-copy events) | 0 mismatches in either direction |
| Producer→sink latency, median of per-batch p50 | 1.69 s (2 s trigger) |
| Producer→sink latency, max of per-batch p95 | 3.91 s |
| Processed rows/s (median / max over micro-batches) | 4,508 / 6,343 |
| Alerts scored against the batch reference | 516 (pipeline evidence only: the replay window overlaps the reference snapshot, RT-10) |

The input rate was capped by the producer (2,000/s). The throughput numbers therefore describe this workload, not the system's limit.

Before the red-team fix (RT-01), a malformed message could advance the watermark and drop all later events. The regression test is `StreamingSpec`, "invalid and unknown-schema messages never reach silver and never move the watermark".

### C.3 HDFS (Docker: 1 NameNode + 3 DataNodes, replication 3)
See `results/hdfs/summary.md`.
* The full silver layer (692 MB, 1,743 files) loaded in 200 s.
* fsck reported HEALTHY, with 0 missing and 0 corrupt blocks. Under-replication fell from 146 blocks after the load to 6 as replication converged.
* With datanode2 stopped, a probe file read in full with an identical checksum.
* All three DataNodes share one physical disk, and there is no NameNode HA.

### C.4 Spark standalone cluster over HDFS (Docker, one host)
`results/hdfs/cluster_bench.txt` and the `results/scalability/runs.jsonl` rows with `master = spark://spark-master:7077`. Setup: 2 workers × 3 cores, executors with 1 GB each, reading `hdfs://namenode:9000/agri/silver/daily_market_prices`, real 2024–2025 rows (11,267,499):

| Workload | Seconds | Rows/s | Shuffle write | Spill (disk) |
|---|---:|---:|---:|---:|
| W1 aggregate (commodity × state × month) | 9.2 | 1.23 M | 37 MB | 63 MB |
| W2 per-entity window features | 14.4 | 0.78 M | 150 MB | 70 MB |

The first attempt with 2 GB executors failed: executors were OOM-killed (exit 137) inside the 7.75 GB Docker VM alongside the four HDFS containers. This run exercises the distributed code path (driver and executors in separate JVMs, network shuffle, HDFS reads) on one machine. It is **not** multi-machine scaling evidence.

### C.5 Single-host scalability (`scripts/scalability_sweep.sh`, `results/scalability/runs.jsonl`, `paper/figures/scalability.png`)
* **Hardware and setup.** Apple M5, 10 cores (4 performance + 6 efficiency), 16 GB RAM; Spark 4.2.0 local mode, driver 6 GB, 32 shuffle partitions, AQE on.
* **Input.** Real silver Parquet from local disk.
* **Execution.** A `noop` sink forces full execution, so output-write speed is excluded.
* **Metrics.** Collected by a SparkListener.

**Data size (10 cores):**

| Years | Rows | W1 aggregate s | W1 rows/s | W2 windows s | W2 rows/s | W2 shuffle write |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 5.74 M | 5.5 | 1.05 M | 6.3 | 0.91 M | 76 MB |
| 2024–25 | 11.27 M | 5.7 | 1.99 M | 10.1 | 1.11 M | 150 MB |
| 2022–25 | 20.13 M | 11.0 | 1.83 M | 19.4 | 1.04 M | 271 MB |
| 2018–25 | 36.07 M | 22.0 | 1.64 M | 35.5 | 1.02 M | 490 MB |
| 2010–25 | 62.65 M | 37.4 | 1.67 M | 66.0 | 0.95 M | 842 MB |
| 2001–26 | 75.64 M | 42.2 | 1.79 M | 65.9 | 1.15 M | 1,023 MB |

Run time grows roughly linearly with input (about 1.6–2.0 M rows/s for W1, about 1.0 M rows/s for W2). No spill to disk was recorded at any size.

**Cores (36.07 M rows, `local[k]`):**

| k | W1 s | speed-up | W2 s | speed-up |
|---:|---:|---:|---:|---:|
| 1 | 33.4 | 1.0 | 95.4 | 1.0 |
| 2 | 19.9 | 1.7 | 54.3 | 1.8 |
| 4 | 13.6 | 2.5 | 36.1 | 2.6 |
| 8 | 14.4 | 2.3 | 32.9 | 2.9 |
| 10 | 14.2 | 2.4 | 31.3 | 3.0 |

Scaling flattens after 4 cores, which matches the number of performance cores. Parquet decoding and the sort are memory-bandwidth bound on one laptop. Single-host core scaling says little about cluster scaling.

**Shuffle partitions × AQE (W2, 36.07 M rows, 10 cores):** 25.6–31.5 s across {8, 32, 128, 512} × {AQE on, off}. AQE off was 1–3 s faster at every setting. Locally, AQE's re-planning overhead exceeds its coalescing benefit; on a cluster with real skew this may differ, which was not tested. The first run at 8 partitions (31.5 s) includes cache warm-up.

**Synthetic workload.** The 350 M-row `synthetic_scaled` workload from v1 was **not** re-run in this session.

## Part D: official-data refresh and evaluation of frozen models (2026-10-23)

### D.1 Back-fill
* **Command.** `python -m agri.ingest.backfill --from 2025-10-01 --to 2026-10-22`, from the data.gov.in variety-wise resource `35985678-…`.
* **Volume.** 387 days, **7,720,662 records**, 1,736 requests, 2 retries, 0 failed days; about 12 s per day at 1 request/s with 5,000-record pages.
* **Run manifests.** `results/ingest/backfill_*.json`.
* **Landing format.** Gzip NDJSON per date with `_SUCCESS` markers. Re-runs skip completed days.

### D.2 Silver v2 and the revision report (`ingestion/IngestLanding.scala`, `results/ingest/revision_report.json`)
* **Contents.** Silver v2 = Kaggle archive before 2025-10-01 (74,488,699 rows) + official records from 2025-10-01 (7,625,384 after de-duplication) = **82.1 M rows**.
* **Overlap 2025-10-01 → 2026-04-21.**
  * The archive holds 1,156,102 of 3,858,695 official reports (**30.0%**).
  * Every archive record was found in the official data.
  * 99.33% have identical modal prices; the 8,438 that differ are source revisions or mirror errors, and silver v2 keeps the official value.

### D.3 Features v2
* **Build.** `AGRI_HISTORY_START=2023-10-01 AGRI_PANEL_FROM=data/forecast/panel_entities`, into `data/forecast_v2/features`. History from 2023-10 reproduces the features of origins from 2025 on. Panel eligibility is reused from the main experiment (2021–23).
* **Run time.** 84 s.
* **Collisions.** 187,264 same-day collisions were resolved (`results/forecast_v2/panel_report.json`):
  * mostly the same market published with and without " APMC";
  * plus 85,315 entity-days with several grades.

### D.4 Frozen models re-scored (`forecast/ForecastProspective.scala`)
* **What is fixed.** Models, conformal quantiles and MASE scales from `fc_main_v3`. Nothing was refitted.
* **Panel.** The main experiment's 11,845 series.
* **Outputs.** `results/forecast/fc_main_v3/{test_complete,prospective}/` and `stats.json`.

| Horizon | Test, complete data: rel. MAE | 80% cov. | DM p | series better | Prospective 2026-04-22 → 10-22: rel. MAE | 80% cov. | DM p | series better |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| next | 0.972 | 79.2% | 3e-49 | 58.7% | **0.963** | 76.9% | 1e-36 | 59.3% |
| h3 | 0.954 | 79.6% | 9e-116 | 69.0% | **0.955** | 78.8% | 3e-42 | 64.1% |
| h7 | 0.943 | 80.0% | 6e-53 | 74.9% | **0.958** | 79.6% | 4e-21 | 66.6% |
| h14 | 0.925 | 80.3% | 3e-41 | 77.2% | **0.952** | 80.1% | 1e-15 | 66.0% |

Test rows per horizon are 1.82–1.97 M on complete data and 0.27–0.31 M prospectively. The prospective set is smaller because it spans 6 months, not 16, and only panel series are scored.

**Sub-periods on complete data:**

| Horizon | Rel. MAE before Nov 2025 | after | 80% coverage before | after |
|---|---:|---:|---:|---:|
| next | 0.970 | 0.976 | 79.5% | 78.0% |
| h3 | 0.952 | 0.962 | 79.9% | 78.7% |
| h7 | 0.938 | 0.962 | 80.3% | 78.7% |
| h14 | 0.923 | 0.937 | 80.7% | 78.5% |

**Correction to B.4.** On the archive, post-migration coverage was 67.6–72.9% and gains appeared to shrink sharply. On complete data the shift is small: coverage falls by 1.2–2.2 points and relative MAE rises by 0.006–0.024. Most of B.4's degradation came from the mirror's missing reports. Those made series artificially sparse and the reported "next" prices further apart.

**Prospective verdict.** Six months after the archive ends, with no refitting, the models beat persistence by 4–5% at every horizon, significantly, and the intervals stay within 3.1 points of nominal coverage. The improvement at 7–14 days is smaller than in the main test (0.958 vs 0.938 at h7), consistent with models trained only to 2023 ageing. Retraining was evaluated afterwards in Part E.1 and did not measurably help.

### D.5 Current serving data
`ForecastPublish exp=fc_main_v3 origin=official` on silver v2 / features v2:
* `data_as_of` 2026-10-22;
* 58,637 latest prices;
* 14,212 forecast entities (10,422 supported);
* 12,056 alerts.

The app's decision cards are therefore current, not expired, until the data is more than 3 days old.

### D.6 Live current-day path
On 2026-10-23 the current-day resource `9ef84268-…` (4 records at 05:36 IST) was pulled by `agri.ingest.cli live` into Kafka. From there it went through `PriceEventStream` into silver: 4/4 records, producer→sink about 2–3 s, `data_origin: live`, "Keralam" normalised to "Kerala" (`results/streaming_live/`).

## Part E: retraining, stronger baseline and feature-timing checks (2026-10-23)

### E.1 Retraining with data to 2025 (`fc_retrain_2025`)
* **Command.** `scripts/retrain_recent.sh` (142 min on the laptop). It builds features on silver v2 in 4 commodity shards (`conf/shards/`), then runs `ForecastBenchmark exp=fc_retrain_2025` with `AGRI_TRAIN_END=2024-12-31 AGRI_VAL_START=2025-01-01 AGRI_VAL_END=2025-12-31 AGRI_TEST_START=2026-01-01`, and scores the frozen `fc_main_v3` models on the same test with `ForecastProspective ... label=final_test_2026`.
* **Splits.**
  * Train origins 2016-01-01 .. 2024-12-31, with targets purged at 2024-12-31.
  * Validation 2025, used for selection and conformal calibration.
  * **Untouched final test 2026-01-01 .. 2026-10-22.**
  * The grid and features are identical to `fc_main_v3`; nothing was tuned on 2026.
* **Selected on 2025 validation.**
  * next: GBT absolute loss d7/i150/s0.5, validation MAE 182.2 vs persistence 187.2.
  * h3: GBT absolute loss d6/i300/s0.25 (232.0 vs 243.1).
  * h7: RF 60×10 (293.5 vs 311.9).
  * h14: GBT squared loss d6/i200 (372.8 vs 405.0).

| Horizon | Persistence MAE ₹/q | Rel. MAE frozen | Rel. MAE retrained | DM p retrained vs frozen | DM p vs persistence (frozen / retrained) | 80% cov. frozen / retrained |
|---|---:|---:|---:|---:|---:|---:|
| next | 202.3 | 0.965 | 0.966 | 0.12 | 6e-55 / 2e-54 | 77.0% / 77.5% |
| h3 | 252.9 | 0.955 | 0.955 | 0.99 | 4e-77 / 2e-76 | 78.6% / 78.8% |
| h7 | 317.3 | 0.958 | 0.958 | 0.74 | 7e-44 / 1e-46 | 79.3% / 78.9% |
| h14 | 411.5 | 0.946 | 0.950 | 0.35 | 2e-27 / 1e-12 | 79.7% / 78.1% |

* **Other baselines on this test** (rel. MAE, retrained run): MA7 1.007–1.130; MA30 1.199–1.745; seasonal naive 1.99–3.98; seasonally adjusted 1.10–1.31. All are worse than persistence.
* **Comparison.** Source: `results/forecast/fc_retrain_2025/comparison_vs_frozen.json`. The DM tests use daily mean absolute-error differences, with the HLN correction and lag h+3 (7 for next).

**Verdict.**
* Retraining on two more years gives **no measurable improvement** at any horizon.
* The frozen models remain significantly better than persistence on 2026.
* The serving model is unchanged (`fc_main_v3`).
* This is a null result for "retrain annually". It does not show that retraining never helps, only that this one refit, with this model class, did not help on this test.
* **Disclosure.** Months 4–10 of 2026 had already been used to score the frozen models (Part D). No retraining decision used any 2026 data.

### E.2 Global LightGBM baseline (`py/agri/analysis/lgbm_baseline.py`)
* **Setup.**
  * Same features, panel and `fc_main_v3` periods; 2 M-row training sample; L1 objective.
  * Validation (2024) chooses `num_leaves` ∈ {63, 255} with early stopping.
  * The test is scored once, as the mean of 3 seeds, on rows joined to the MLlib test predictions.
* **Output.** `results/forecast/fc_main_v3/lgbm_baseline.json`.

| Horizon | Val MAE (63 / 255 leaves) | Chosen | Rounds | Rel. MAE MLlib selected | Rel. MAE LightGBM | DM p |
|---|---:|---:|---:|---:|---:|---:|
| next | 199.4 / 199.1 | 255 | 886 | 0.971 | 0.944 | 2e-92 |
| h3 | 260.6 / 260.4 | 255 | 901 | 0.953 | 0.926 | 6e-73 |
| h7 | 336.0 / 335.2 | 255 | 844 | 0.938 | 0.915 | 3e-09 |
| h14 | 426.7 / 426.0 | 255 | 329 | 0.923 | 0.892 | 1e-10 |

**LightGBM is better than the production MLlib model at every horizon** (by 0.023–0.031 rel. MAE). The served model is therefore not the best one measured. LightGBM is not served, because the serving and publish path is Spark and porting it has not been done. See KNOWN_LIMITATIONS #12.

### E.3 Same-day cross-market features (`py/agri/analysis/crosssection_timing.py`)
The LightGBM configuration from E.2 (seed 1) was refitted with the cross-market features:
* same-day (as published);
* recomputed from the **previous** day, which is always available at the origin;
* removed.

The Spark benchmark supports the same lag via `crossSection=lag1`.

| Horizon | same day | previous day | none |
|---|---:|---:|---:|
| next | 0.946 | 0.948 | 0.955 |
| h7 | 0.918 | 0.922 | 0.932 |
| h14 | 0.893 | 0.899 | 0.908 |

Lagging the features costs 0.002–0.006, while removing them costs 0.009–0.015. Most of their contribution does not depend on same-day publication. Source: `results/forecast/fc_main_v3/crosssection_timing.json`.
