# Response to the supplied Q1 review: locked retrospective protocol

This protocol and implementation are committed before the revision experiments run. The
original results remain historical/exploratory; this study cannot supply independent
confirmation because all 2026 prices have already been inspected.

## Resource-limited robustness experiment

* Preserve production model, gold, original data and main results.
* Original filtered features: `data/forecast_v3/features`.
* Build a second feature table retaining ×5-flagged reports from silver v2, four
  commodity shards, history from 2022-10-01. All 2024 origins have over a year of
  warm-up. Preserve original panel membership. All other validation rules remain.
* Train origins: 2024-01-01..2024-12-31. Training targets must be dated by Dec 31.
* Selection: 2025-01-01..2025-06-30 (targets purged at June 30).
* Calibration: 2025-07-01..2025-12-31 (targets purged at Dec 31), entirely separate
  from selection, early stopping, categories and hyperparameter selection.
* Retrospective evaluation: 2026-01-01..2026-10-22, origins and targets within period.
* LightGBM L1, 500,000 deterministic hash-sampled training rows, seed 20261023,
  leaves {31,63}, at most 800 iterations, early stopping 75 on selection data only;
  remaining parameters from the existing candidate. One seed. This smaller model
  tests robustness; it is not a reproduction of the full-size main model.
* Persistence, 7/30-day geometric averages, seasonal naive with persistence fallback,
  seasonally adjusted persistence on identical eligible rows. Row-level MASE uses
  per-entity mean absolute naive price change computed only from training data.
* Residual quantiles and volatility quintiles fitted on calibration data only.
* Report each cleaning regime on all its own eligible rows and both on common
  (entity,origin) keys. Cleaning can change targets and features, even on shared
  origins; the comparison tests pipeline sensitivity, not causal identification.
* Inspect a deterministic sample of flagged observations, without declaring any
  genuine shock erroneous merely because it exceeds the threshold.

## Statistical reporting

Primary family: candidate vs persistence, 4 horizons × 2 cleaning regimes = 8
comparisons, two-sided DM p values on calendar-day total loss differences (scaled by a constant, so they target pooled MAE) corrected together using Holm at alpha .05.
Preserve raw p values. Circular moving-block bootstrap of calendar-day error sums,
block sizes 14 and 28 days, 500 repetitions, seed 20261023; report percentile 95%
intervals for relative MAE and difference in MAE. Separately bootstrap entity clusters
(500 repetitions) to describe heterogeneity across markets. These are conditional
on fitted models, not full training uncertainty; cluster/day estimates are not
combined into a claim of two-way robust inference. Monthly results and MASE remain
prominent regardless of whether they favour the candidate.

## Reproducibility

Capture exact source commit, SHA256 of source files, config, input Parquet files,
model files, dependencies, runtime and split row/date bounds. Abort training when
tracked implementation differs from the locked commit. Output manifests and tables
are regenerated from checksum-verified saved predictions; no manually entered numeric tables. Imported helper and dependency paths are recorded. Feature reuse requires a sealed build manifest binding input/output hashes, builder source hashes and settings. Untracked implementation files are rejected. Historical cleaned-feature construction is disclosed separately; byte hashes do not prove its original build code.

## Independent future confirmation

A genuine prospective test remains pending. Lock current serving boosters and
preprocessing hashes before 2026-10-24. Only forecasts actually issued before their
target dates qualify; a later backcast is excluded. A minimum of 90 completed calendar
days is required. Selection and calibration remain frozen. The current session cannot
observe these future outcomes. Do not call the historical 2026 results confirmatory.
