#!/usr/bin/env bash
# Retraining experiment on the complete official record (silver v2).
#   scripts/retrain_recent.sh [EXP]
# Protocol, fixed before running (docs/EXPERIMENTS.md Part E):
#   train origins 2016-01-01..2024-12-31 | validation 2025 (tuning + conformal) |
#   FINAL TEST 2026-01-01..2026-10-22, scored once. Same search space, selection rule,
#   sample sizes and seed as fc_main_v3. Panel = fc_main_v3 panel (2021-23 eligibility).
# Then the FROZEN fc_main_v3 models are scored on the identical final test for comparison.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
EXP="${1:-fc_retrain_2025}"
ROOT=data/forecast_v3
export AGRI_SILVER_DAILY=data/processed/daily_market_prices_v2 AGRI_FORECAST_ROOT=$ROOT AGRI_RESULTS_ROOT=results/forecast_v3
export AGRI_PANEL_FROM=data/forecast/panel_entities
mkdir -p logs results/forecast_v3
if [ ! -f "$ROOT/features/_SUCCESS" ] || [ "${REBUILD_FEATURES:-0}" = 1 ]; then
  # 4 commodity shards (features and cross-sections are per commodity, so this is exact);
  # a single build needs ~40 GB of shuffle space, more than this laptop has free.
  mode=overwrite
  for s in a b c d; do
    AGRI_FORECAST_COMMODITIES=conf/shards/commodities_$s.txt AGRI_SHARD_TAG=$s AGRI_FEATURES_WRITE_MODE=$mode \
      scripts/submit.sh com.agribigdata.forecast.BuildForecastFeatures > logs/${EXP}_features_$s.log 2>&1
    mode=append
  done
fi
AGRI_TRAIN_END=2024-12-31 AGRI_VAL_START=2025-01-01 AGRI_VAL_END=2025-12-31 AGRI_TEST_START=2026-01-01 \
  AGRI_RESULTS_ROOT=results/forecast \
  scripts/submit.sh com.agribigdata.forecast.ForecastBenchmark "exp=$EXP" > logs/${EXP}_benchmark.log 2>&1
AGRI_RESULTS_ROOT=results/forecast \
  scripts/submit.sh com.agribigdata.forecast.ForecastProspective exp=fc_main_v3 features=$ROOT/features \
    models=data/forecast/models/fc_main_v3 from=2026-01-01 to=2026-10-22 label=final_test_2026 > logs/${EXP}_frozen_on_final.log 2>&1
echo "retrain $EXP complete"
