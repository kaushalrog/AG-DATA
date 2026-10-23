#!/usr/bin/env bash
# Run only from a committed source tree. Output tables are generated automatically.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
COMMIT=$(git rev-parse HEAD)
[ -z "$(git status --porcelain --untracked-files=all -- py src scripts conf docs/REVISION_PROTOCOL.md)" ] || { echo 'Commit implementation first' >&2; exit 1; }
mkdir -p logs results/revision_q1
sbt -batch assembly > logs/revision_assembly.log 2>&1
if [ ! -f data/revision_unfiltered/RESEARCH_COMPLETE ]; then
  [ ! -d data/revision_unfiltered ] || { echo 'Partial build exists: inspect before restarting (no automatic deletion)' >&2; exit 1; }
  mode=overwrite
  for shard in a b c d; do
    .venv/bin/python -c 'import shutil; assert shutil.disk_usage(".").free>6*1024**3,"Need at least 6 GiB free"'
    AGRI_DRIVER_MEMORY=4g AGRI_SILVER_DAILY=data/processed/daily_market_prices_v2 \
      AGRI_FORECAST_ROOT=data/revision_unfiltered AGRI_RESULTS_ROOT=results/revision_q1 \
      AGRI_HISTORY_START=2022-10-01 AGRI_PANEL_FROM=data/forecast/panel_entities \
      AGRI_FORECAST_COMMODITIES=conf/shards/commodities_$shard.txt AGRI_SHARD_TAG=$shard \
      AGRI_FEATURES_WRITE_MODE=$mode AGRI_APPLY_JUMP_RULE=false \
      AGRI_EXCLUDED_SAMPLE=data/revision_q1/excluded_$shard \
      scripts/submit.sh com.agribigdata.forecast.BuildForecastFeatures > logs/revision_features_$shard.log 2>&1
    mode=append
  done
  touch data/revision_unfiltered/RESEARCH_COMPLETE
  PYTHONPATH=py .venv/bin/python -m agri.research.build_manifest seal
fi
PYTHONPATH=py .venv/bin/python -m agri.research.build_manifest verify
PYTHONPATH=py .venv/bin/python -m agri.research.revision run --commit "$COMMIT" > logs/revision_experiment.log 2>&1
