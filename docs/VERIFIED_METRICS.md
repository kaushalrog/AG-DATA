# Verified metrics: single source of truth

Every number that may appear in the README, paper, slides, viva material or the app must come from this table. The **source** column is the file the number is read from. Anything not listed here must not be presented as a measured result.

Status: 2026-10-23. All runs referenced here have completed.

## 1. Data (silver layer and back-fill)
| Quantity | Value | Source |
|---|---|---|
| Archive rows (raw, Kaggle `khandelwalmanas/daily-commodity-prices-india` v134) | 75,984,017 | `PROJECT_STATUS.md` §3.2 (profiling job) |
| Archive silver rows after quality + de-duplication | 75,644,801 | DuckDB count of `data/processed/daily_market_prices` |
| Silver v2 rows (archive < 2025-10-01 + official data.gov.in from 2025-10-01) | 82,114,083 (74,488,699 + 7,625,384) | `results/ingest/revision_report.json` |
| Official records back-filled, 2025-10-01 → 2026-10-22 | 7,720,662 over 387 days, 0 failed days | `results/ingest/backfill_*.json` |
| Archive share of official records, 2025-10-01 → 2026-04-21 | 30.0% | `results/ingest/revision_report.json` |
| Matched archive records with identical modal price | 99.33% (8,438 differ) | same |
| Forecast panel | 36 commodities, 11,845 series, 21.06 M feature rows | `results/forecast/panel_report.json` |
| Share of exactly-zero target changes (2024 validation) | next 34.4%, h3 27.9%, h7 21.8%, h14 17.2% | `docs/EXPERIMENTS.md` A.10 (DuckDB query) |

## 2. Forecasting, experiment `fc_main_v3`
**Periods.**
* Train origins 2016-01-01 .. 2023-12-31.
* Validation 2024.
* Test 2025-01-01 .. 2026-04-20, archive data; this is the last date with panel rows.

Source: `results/forecast/fc_main_v3/manifest.json`. Models: `data/forecast/models/fc_main_v3/<h>/<family>`; parameters are in `results/forecast/fc_main_v3/model_artifacts.json`.

**Selected models.**
* next and h3: GBT, absolute loss, percent target (depth 7, 150 iterations, step 0.5).
* h7 and h14: random forest (60 trees, depth 10).

| Horizon | Persistence MAE ₹/q | Selected MAE | Rel. MAE | 80% coverage | DM p | Series better | Source |
|---|---:|---:|---:|---:|---:|---:|---|
| next | 189.0 | 183.5 | 0.971 | 78.6% | 1.3e-22 | 58.5% | `metrics_overall.csv`, `intervals.csv`, `dm_tests.csv`, `test_series_wins.json` |
| h3 | 242.6 | 231.1 | 0.953 | 79.4% | 3.6e-47 | 68.8% | same |
| h7 | 308.8 | 289.7 | 0.938 | 80.0% | 4.4e-39 | 75.0% | same |
| h14 | 397.0 | 366.4 | 0.923 | 80.5% | 8.7e-29 | 76.4% | same |

| Evaluation of the frozen models (no refitting) | next | h3 | h7 | h14 | 80% coverage | Source |
|---|---:|---:|---:|---:|---:|---|
| Same test period, complete official data | 0.972 | 0.954 | 0.943 | 0.925 | 79.2–80.3% | `results/forecast/fc_main_v3/test_complete/` |
| Prospective 2026-04-22 → 2026-10-22 | 0.963 | 0.955 | 0.958 | 0.952 | 76.9–80.1% | `results/forecast/fc_main_v3/prospective/` |
| Rolling-origin folds 2021–2024 (range) | 0.970–0.976 | 0.952–0.960 | 0.936–0.946 | 0.920–0.936 | — | `backtest_*.csv` |
| Per-series SES on 400 sampled series (SES / global model) | 0.975 / 0.976 | 0.962 / 0.960 | 0.967 / 0.946 | 0.975 / 0.935 | — | `stat_baseline_ses.json` |

*Prospective* here means a post-development hold-out. The models were saved on 2026-10-22, and the official reports after 2026-04-21 were first downloaded on 2026-10-23 (`model_artifacts.json`, `results/ingest/backfill_*.json`). The forecasts were not issued in real time.

DM robustness: with a Newey–West lag of 20, every horizon still gives p ≤ 7.9e-13 (`results/forecast/fc_main_v3/dm_tests_lag20.json`).

Rel. MAE = MAE of the model ÷ MAE of persistence on identical rows (lower is better; < 1 beats "last price").

**Global LightGBM baseline (L1, same features, 2M-row sample, tuned and early-stopped on 2024 validation only, mean of 3 seeds).** Source: `results/forecast/fc_main_v3/lgbm_baseline.json`. Test rows are identical to those of the MLlib model.

| Horizon | Rel. MAE, MLlib selected | Rel. MAE, LightGBM | DM p (LightGBM vs MLlib) | Seed MAE spread (₹/q) |
|---|---:|---:|---:|---:|
| next | 0.971 | **0.944** | 1.6e-92 | 0.02 |
| h3 | 0.953 | **0.926** | 6.3e-73 | 0.05 |
| h7 | 0.938 | **0.915** | 3.1e-9 | 0.26 |
| h14 | 0.923 | **0.892** | 1.4e-10 | 1.15 |

LightGBM is significantly better than the production MLlib model at every horizon. The MLlib model is therefore **not** the best model available for this task.

**Decision cards, test period, h7.** WATCH on 98.5% of report-days. HOLD on 0.5%, hit rate 80.0%. SELL on 1.0%, hit rate 67.8%. Source: `decisions.csv`.

## 3. Anomaly detection (injected corruptions, run `results/anomaly/20261022T175225Z`)
| Detector | PR-AUC (any corruption) | Precision | Recall | FPR |
|---|---:|---:|---:|---:|
| Production rule (trailing robust z) | 0.704 | 0.313 | 0.846 | 0.019 |
| Previous-report change | 0.671 | 0.160 | 0.960 | 0.051 |
| Legacy commodity IQR (v1 rule) | 0.352 | 0.208 | 0.371 | 0.014 |

There are no labels for real anomalies. **No accuracy figure for real anomalies exists.**

## 4. Retraining `fc_retrain_2025` (completed 2026-10-23)
**Protocol.** Train origins 2016-01-01 .. 2024-12-31; validation 2025 (model and hyper-parameter selection only); final test 2026-01-01 .. 2026-10-22, not used for any retraining choice; it overlaps the main test (Jan–Apr) and the frozen hold-out (Apr–Oct) (silver v2, official records). Same feature definitions, panel and model grid as `fc_main_v3`. Selected on validation: next GBT, h3 GBT, h7 RF, h14 GBT. Sources: `results/forecast/fc_retrain_2025/manifest.json` (`completed: true`), `tuning.csv`, `metrics_overall.csv`, `intervals.csv`, `comparison_vs_frozen.json`. Command: `scripts/retrain_recent.sh` (142 min).

**Comparison on identical 2026 test rows** with the frozen `fc_main_v3` models (trained to 2023, not refitted; `results/forecast/fc_main_v3/final_test_2026/`).

| Horizon | Test rows | Persistence MAE ₹/q | Rel. MAE frozen | Rel. MAE retrained | DM p (retrained vs frozen) | 80% coverage frozen / retrained | Best other baseline (rel.) |
|---|---:|---:|---:|---:|---:|---:|---:|
| next | 553,801 | 202.3 | 0.965 | 0.966 | 0.12 | 77.0% / 77.5% | 1.101 |
| h3 | 531,321 | 252.9 | 0.955 | 0.955 | 0.99 | 78.6% / 78.8% | 1.043 |
| h7 | 519,251 | 317.3 | 0.958 | 0.958 | 0.74 | 79.3% / 78.9% | 1.023 |
| h14 | 496,306 | 411.5 | 0.946 | 0.950 | 0.35 | 79.7% / 78.1% | 1.007 |

Both models beat persistence at every horizon (DM p ≤ 1.4e-12). The other baselines (MA7, MA30, seasonal naive, seasonally adjusted) are all worse than persistence (rel. MAE > 1).

**Finding.** Adding 2024–2025 data did **not** produce a measurable improvement: no difference is significant (p 0.12–0.99), and the retrained h14 model is numerically slightly worse. The frozen models remain defensible on 2026 data in the sense that they still beat persistence by 3.5–5.4%. That does not make them "current": they encode nothing after 2023. `AGRI_SERVING_MODEL` stays `fc_main_v3`; switching is not justified by this evidence.

**Disclosure.** The 2026-04-22 .. 2026-10-22 slice had already been used to score the frozen models (prospective check, §2). No retraining choice used any 2026 data.

**Cross-market timing (LightGBM, `fc_main_v3` periods, seed 1).** Source: `results/forecast/fc_main_v3/crosssection_timing.json`. Rel. MAE with same-day / previous-day / no cross-market features:
* next: 0.946 / 0.948 / 0.955;
* h7: 0.918 / 0.922 / 0.932;
* h14: 0.893 / 0.899 / 0.908.

Lagging the cross-market features by one day (always published before the forecast origin) costs only 0.002–0.006. Most of their value is therefore not an artefact of same-day publication timing.

## 4b. Serving switch to LightGBM `fc_lgbm_2025` (2026-10-23)
**Pre-registration.** The rule was committed before training (`docs/PREREG_LGBM_SWITCH.md`, commit `662c2c7`).

**Candidate.**
* Global LightGBM, L1 loss, one booster per horizon, seed 1.
* Same features, panel and periods as `fc_retrain_2025`: train 2016–2024 on a 2 M-row sample; validation 2025, used only for `num_leaves` ∈ {63, 255}, early stopping and the conformal fit.
* Chosen: next: 255 leaves, 503 rounds; h3: 255 leaves, 908 rounds; h7: 255 leaves, 320 rounds; h14: 255 leaves, 106 rounds.
* Validation MAE: next 177.5 vs persistence 187.3; h3 226.5 vs persistence 243.7; h7 287.2 vs persistence 313.2; h14 365.0 vs persistence 405.8.
* Command: `python -m agri.forecast.lgbm train`, then `test`. Sources: `results/forecast/fc_lgbm_2025/{manifest.json, tuning.csv, final_test_2026.json, switch_decision_statistical.json, publish_parity.json}`.

**Final test 2026-01-01 .. 2026-10-22, identical rows for all three models.** The Holm-adjusted DM p compares LightGBM with frozen `fc_main_v3`.

| Horizon | Rows | Rel. MAE frozen | Rel. MAE retrained (Spark) | Rel. MAE LightGBM | Holm p | 80% coverage frozen / LightGBM |
|---|---:|---:|---:|---:|---:|---:|
| next | 553,801 | 0.965 | 0.966 | **0.944** | 2e-102 | 77.0% / 77.5% |
| h3 | 531,321 | 0.955 | 0.955 | **0.933** | 4e-93 | 78.6% / 78.7% |
| h7 | 519,251 | 0.958 | 0.958 | **0.934** | 1e-30 | 79.3% / 79.0% |
| h14 | 496,306 | 0.946 | 0.950 | **0.922** | 4e-16 | 79.7% / 78.7% |

**Decision rule outcome.**
1. Better at h7 after Holm correction: **pass**.
2. No horizon significantly worse: **pass**. LightGBM is better at every horizon, and also better than the retrained Spark models (p ≤ 4e-30).
3. Coverage within 75–85% and no more than 2 points worse than frozen: **pass**.
4. Operational: **pass**.
   * The staged candidate release passed `validate_release`.
   * The published medians equal the scored predictions and an offline re-prediction, max |Δ| = 0.0 over 56,848 rows (`publish_parity.json`).

**Decision.**
* The serving default is now `AGRI_SERVING_MODEL=fc_lgbm_2025`.
* The live gold was switched by a normal refresh: run `20261023T083639194149Z`, `ok: true`.
* Roll back with `AGRI_SERVING_MODEL=fc_main_v3 scripts/refresh.sh --skip-fetch`, or re-point `data/gold` to release `20261023T062346924428Z`.

**Caveats (from the pre-registration).**
* The 2026 test had been used twice before.
* This is the third model scored on it.
* The earlier LightGBM result on overlapping data motivated the test.

The gain (0.021–0.024 rel. MAE against frozen) is real on this test, but it is not an independent confirmation. LightGBM still uses same-day cross-market features. With a one-day lag it loses only 0.002–0.006 (§4).

## 5. Systems
| Quantity | Value | Source |
|---|---|---|
| Streaming replay | 21,524 messages = 20,000 to silver + 1,317 duplicates removed + 207 quarantined; 0 missing; parity 0 mismatches; producer→sink p50 1.69 s | `results/streaming/demo_summary.json`, `parity.json` |
| Live current-day pull (2026-10-23) | 4/4 records through Kafka to silver | `results/streaming_live/` |
| HDFS | 692 MB silver, replication 3, HEALTHY; readable with 1 DataNode down | `results/hdfs/summary.md` |
| Spark cluster (Docker, 2 workers × 3 cores, one host) | 11.27 M rows: W1 9.2 s, W2 14.4 s | `results/hdfs/cluster_bench.txt` |
| Local scaling (Apple M5, 10 cores) | full 75.6 M rows: W1 42.2 s, W2 65.9 s; speed-up at 10 cores: 2.4× (W1), 3.0× (W2) | `results/scalability/runs.jsonl` |
| Tests | Scala 22, Python 80 locally (some skipped in CI without data), app 56, browser end-to-end 15 checks | local runs 2026-10-23 (`logs/final_sbt.log`); CI run 39899466902 |

## 6. Withdrawn claims (never use)
| Claim | Why |
|---|---|
| 95.66% accuracy, 86.55% precision, 85.47% recall, 86.01% F1, ROC-AUC 0.948, FPR 2.46%, "48,354 test records" | Not produced by any code or log in the repository. They were introduced in commit `d760677`, which edited only the README and dashboard (`docs/AUDIT_PRIOR_RESULTS.md`) |
| "Zero data leakage" for the v1 classifier | v1 labels were functions of the features, and the outlier bounds were fitted on all years including the test period |
| v1 next-observation classifier, 72.54% accuracy | It was logged, but it is below the 84.35% all-normal baseline. Quote it only together with that baseline |
| "1,200 events/sec", "< 800 ms latency", "15,000-record replay" | No result file in the repository records these numbers. Use section 5 instead |
| "93.41 M records" | That is the v1 canonical table that combined both sources; it is not the silver layer. Use 75.6 M (archive silver) or 82.1 M (silver v2) |
| "End-to-end exactly-once" | Not claimed; see `docs/ARCHITECTURE.md` (effectively-once per offset range) |


## Retrospective robustness revision (2026-10-23)

Completed fitting source `e7abad9`; reporting correction `9c93bb7`.
`results/revision_q1/manifest.json` and `TABLES.md` trace all eight model/cleaning
comparisons to checksum-verified saved predictions. Training: 2024 (500k sample);
selection: Jan–Jun 2025; calibration: Jul–Dec 2025; evaluation: Jan–Oct 22 2026.
Relative MAE cleaned next/h3/h7/h14: .951/.943/.952/.957; unfiltered:
.951/.941/.950/.955. All five simple baselines included. MASE remains above one;
80% coverage 77.7–79.5%. Temporal block and entity-cluster intervals, monthly
results, common origins and Holm-eight tests are in the generated tables.
This is retrospective sensitivity, not independent confirmation or a serving switch.
Post-build feature fingerprints cannot reconstruct exact historical execution state.
The superseded d624416 manifest is invalid and must never supply reported metrics.

## Clean-source release-study reproduction (second review)

Fitting source `e233b40`, immutable tag `agdata-research-source-v1`; reporting source
`cd1f786`. `results/release_v1/manifest.json` contains both complete pre/post build
records, model/prediction checksums, fitted split bounds and all statistical outputs.
Both cleaning variants were freshly rebuilt from retained silver v2 and the same
fixed historical panel, history from October 2022. No historical feature bytes reused.
This repeats the smaller 2024-training study, **not** the full-size historical MLlib
experiments or panel selection. Model fitting took 230.8 s (build/hash/report excluded).

| Horizon | Cleaned relative MAE | Unfiltered relative MAE |
|---|---:|---:|
| next | .951 | .951 |
| h3 | .943 | .941 |
| h7 | .950 | .950 |
| h14 | .956 | .955 |

Observed pooled MAE reductions: 4.4–5.9%, INR 9.92–18.83/quintal; each fit contains
281–294 calendar days and 4,602–5,182 entities. The records are not independent
replicates. MASE excludes 4.4–4.5% of evaluation rows without usable training scales.
Six dependence specifications per fit (circular/non-circular × 28/42/56-day blocks,
2,000 replicates) are retained, alongside HAC bandwidth sensitivities without HLN.
Their interval endpoints span .936–.962, not a combined confidence interval. Daily
ACF remains material at long lags; coverage and stationarity are not established.
46 overlapping state/commodity group-by-fit comparisons favour persistence. No
subgroup multiplicity-adjusted discovery, future confirmation or serving switch.
