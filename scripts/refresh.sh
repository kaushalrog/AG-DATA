#!/usr/bin/env bash
# Daily refresh entry point (cron / launchd / manual). Exit codes: 0 ok, 1 failed (live gold unchanged), 75 already running.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
[ -f .env ] && { set -a; . ./.env; set +a; }
[ -f target/scala-2.13/agri-bigdata-assembly.jar ] || sbt -batch assembly >/dev/null
mkdir -p logs
exec env PYTHONPATH=py .venv/bin/python -m agri.ops.refresh "$@"
