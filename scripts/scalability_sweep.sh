#!/usr/bin/env bash
# Single-host scalability sweeps (local mode). Appends to results/scalability/runs.jsonl.
#   scripts/scalability_sweep.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p results/scalability logs
scripts/submit.sh com.agribigdata.bench.ScalabilityBench mode=size >> logs/scalability.log 2>&1
scripts/submit.sh com.agribigdata.bench.ScalabilityBench mode=partitions >> logs/scalability.log 2>&1
for k in 1 2 4 8 10; do
  MASTER="local[$k]" scripts/submit.sh com.agribigdata.bench.ScalabilityBench mode=cores years=2018-2025 >> logs/scalability.log 2>&1
done
echo done
