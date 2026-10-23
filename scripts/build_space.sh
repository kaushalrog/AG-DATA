#!/usr/bin/env bash
# Assembles a self-contained Hugging Face Space (Docker) from the CURRENT served release:
# app/ + py/agri/api + conf/decision_rules.json + data/gold (dereferenced) + the serving model's
# accuracy files. No API key, no raw data, no Spark.
#
#   scripts/build_space.sh [out_dir]           # default build/space
#   docker build -t agdata-space build/space && docker run -p 7860:7860 agdata-space
#   hf upload <user>/<space> build/space . --repo-type space     # deploy (needs `hf auth login`)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-build/space}"
GOLD="$(python3 -c 'import os;print(os.path.realpath("data/gold"))')"
MODEL="$(python3 -c 'import json;print(json.load(open("data/gold/meta.json"))["model_version"])')"
rm -rf "$OUT"; mkdir -p "$OUT/py/agri" "$OUT/conf" "$OUT/data" "$OUT/results/forecast/$MODEL" "$OUT/results/refresh"
cp deploy/hf-space/{Dockerfile,README.md,requirements.txt} "$OUT/"
cp py/agri/__init__.py "$OUT/py/agri/"
rsync -a --exclude __pycache__ py/agri/api "$OUT/py/agri/"
rsync -a --exclude tests --exclude tools --exclude demo app "$OUT/"  # real API on the same origin: no demo fallback
cp conf/decision_rules.json "$OUT/conf/"
rsync -a --exclude '*.crc' --exclude '_SUCCESS' "$GOLD/" "$OUT/data/gold/"
cp results/forecast/"$MODEL"/{test_by_commodity_*.csv,intervals.csv} "$OUT/results/forecast/$MODEL/"
[ -f results/refresh/status.json ] && python3 - "$OUT" <<'PY'
import json, sys
st = json.load(open("results/refresh/status.json"))  # only what /meta exposes; no paths or errors
json.dump({k: st.get(k) for k in ("ok", "last_success", "last_failure", "failed_step")},
          open(f"{sys.argv[1]}/results/refresh/status.json", "w"))
PY
du -sh "$OUT"; echo "model $MODEL, data_as_of $(python3 -c 'import json;print(json.load(open("data/gold/meta.json"))["data_as_of"])')"
