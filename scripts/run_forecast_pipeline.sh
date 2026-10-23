#!/usr/bin/env bash
# Reproduce the forecasting experiment end to end (local Spark). Stops on the first failure.
#   scripts/run_forecast_pipeline.sh [EXP_ID]
#   REBUILD_FEATURES=1 scripts/run_forecast_pipeline.sh ...   # force F1 even if features exist
# Steps: F1 features -> F2 benchmark (+ablation on h7) -> F2b backtest -> report -> F3 publish gold.
# Requires the silver layer (data/processed/daily_market_prices), produced by
#   sbt "runMain com.agribigdata.preprocessing.PreprocessDatasets"
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
EXP="${1:-fc_$(date +%Y-%m-%d)_$(git rev-parse --short HEAD)}"
mkdir -p logs
LOG="logs/${EXP}.log"
run() {
  echo "==> $*" | tee -a "$LOG"
  set +e
  sbt -batch "runMain $*" >>"$LOG" 2>&1
  local rc=$?
  set -e
  grep -E '^\[info\] (\[F|\[BT|\{)|TIMING' "$LOG" | tail -5 || true
  if [ $rc -ne 0 ]; then echo "FAILED ($rc): $* — see $LOG" >&2; exit $rc; fi
}
if [ ! -d data/forecast/features ] || [ "${REBUILD_FEATURES:-0}" = 1 ]; then
  run com.agribigdata.forecast.BuildForecastFeatures
else
  echo "==> reusing data/forecast/features (built $(stat -f %Sm data/forecast/features)); set REBUILD_FEATURES=1 to rebuild" | tee -a "$LOG"
fi
run com.agribigdata.forecast.ForecastBenchmark "exp=$EXP" ablation=true ablationHorizons=h7
python3 -c "import json,sys; m=json.load(open('results/forecast/$EXP/manifest.json')); sys.exit(0 if m.get('completed') else 'manifest not completed')"
# best GBT configuration on h7 validation MAE (applied to every backtest horizon; see EXPERIMENTS A.3)
SPEC=$(awk -F, 'NR>1 && $1=="h7" && $2=="gbt" {print $4","$3}' "results/forecast/$EXP/tuning.csv" | sort -t, -k1,1g | head -1 | cut -d, -f2)
[ -n "$SPEC" ] || { echo "no GBT spec found in tuning.csv" >&2; exit 1; }
run com.agribigdata.forecast.ForecastBacktest "exp=$EXP" "spec=$SPEC"
PYTHONPATH=py .venv/bin/python -m agri.analysis.forecast_report --exp "$EXP"
run com.agribigdata.forecast.ForecastPublish "exp=$EXP"
echo "experiment $EXP complete: results/forecast/$EXP"
