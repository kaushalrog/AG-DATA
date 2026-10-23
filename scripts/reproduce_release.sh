#!/usr/bin/env bash
# Refuses existing output roots: no historical or production results are overwritten.
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
COMMIT=$(git rev-parse HEAD)
[ -z "$(git status --porcelain --untracked-files=all -- py src scripts conf build.sbt project docs/RELEASE_PROTOCOL.md docs/REVISION_PROTOCOL.md)" ] || { echo 'Commit implementation first' >&2; exit 1; }
[ ! -e results/release_v1/manifest.json ] || { echo 'Release results already exist; inspect rather than overwrite' >&2; exit 1; }
mkdir -p logs
sbt -batch assembly > logs/release_assembly.log 2>&1
for variant in cleaned unfiltered; do
 rule=true; [ "$variant" != unfiltered ] || rule=false
 PYTHONPATH=py .venv/bin/python -m agri.research.release_build build \
   --root "data/release_v1_$variant" --results "results/release_v1/build_$variant" --jump-rule "$rule"
done
PYTHONPATH=py .venv/bin/python -m agri.research.revision run --commit "$COMMIT" \
 --cleaned data/release_v1_cleaned --unfiltered data/release_v1_unfiltered \
 --output results/release_v1 --artifacts data/release_v1 --verified-builds
