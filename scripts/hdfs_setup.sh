#!/usr/bin/env bash
# ================================================================
# Bring up the HDFS cluster and create the /agri directory layout.
#
#   ./scripts/hdfs_setup.sh up        start cluster + create dirs
#   ./scripts/hdfs_setup.sh load      copy raw + processed data in
#   ./scripts/hdfs_setup.sh report    health, replication, block report
#   ./scripts/hdfs_setup.sh down      stop cluster (keeps data)
#   ./scripts/hdfs_setup.sh destroy   stop and WIPE all HDFS data
# ================================================================
set -euo pipefail

cd "$( dirname "${BASH_SOURCE[0]}" )/.."
source scripts/env.sh

COMPOSE="docker compose -f docker/docker-compose.yml"
NN="docker exec agri-namenode"

# Run an hdfs command inside the NameNode container.
hdfs_cmd() { $NN /opt/hadoop/bin/hdfs "$@"; }

require_docker() {
  if ! docker ps >/dev/null 2>&1; then
    echo "ERROR: the Docker daemon is not running."
    echo "Start Docker Desktop, wait for it to report 'running', then retry."
    exit 1
  fi
}

case "${1:-up}" in

  up)
    require_docker
    echo "==> starting HDFS (1 NameNode + 3 DataNodes)"
    $COMPOSE up -d

    echo "==> waiting for the NameNode to leave safe mode"
    # Safe mode is read-only: HDFS stays there until enough blocks have
    # been reported by DataNodes. Creating directories before that
    # fails, so this wait is required, not cosmetic.
    for _ in $(seq 1 40); do
      if hdfs_cmd dfsadmin -safemode get 2>/dev/null | grep -q OFF; then
        echo "    safe mode OFF"
        break
      fi
      sleep 5
    done

    echo "==> creating /agri layout"
    hdfs_cmd dfs -mkdir -p \
      /agri/raw/daily_market_prices \
      /agri/raw/india_mandi \
      /agri/processed/daily_market_prices \
      /agri/processed/india_mandi \
      /agri/features/forecasting \
      /agri/features/anomaly \
      /agri/streaming/checkpoints \
      /agri/results/forecasts \
      /agri/results/anomalies \
      /agri/scaled/synthetic_market_workload

    hdfs_cmd dfs -ls -R /agri | awk '{print $8}'
    echo
    echo "NameNode UI: http://localhost:9870"
    ;;

  load)
    require_docker
    echo "==> loading RAW data into HDFS (this moves ~11 GB, expect minutes)"
    # -f overwrites, so the script is re-runnable. The local data is
    # bind-mounted read-only at /staging, so nothing is copied into the
    # container image first.
    docker exec agri-namenode bash -c "/opt/hadoop/bin/hdfs dfs -put -f /staging/raw/Daily_Market_Prices_2001_2026/csv/*.csv /agri/raw/daily_market_prices/"
    docker exec agri-namenode bash -c "/opt/hadoop/bin/hdfs dfs -rm -r -f /agri/raw/india_mandi && /opt/hadoop/bin/hdfs dfs -put /staging/raw/india_mandi /agri/raw/"

    if [ -d data/processed/daily_market_prices ]; then
      echo "==> loading PROCESSED parquet into HDFS"
      hdfs_cmd dfs -put -f /staging/processed/daily_market_prices \
        /agri/processed/
      hdfs_cmd dfs -put -f /staging/processed/india_mandi \
        /agri/processed/ 2>/dev/null || true
    else
      echo "    (no data/processed yet - run PreprocessDatasets first)"
    fi

    echo "==> usage"
    hdfs_cmd dfs -du -h /agri
    ;;

  report)
    require_docker
    echo "==================== CLUSTER HEALTH ===================="
    hdfs_cmd dfsadmin -report | head -40
    echo
    echo "==================== SPACE BY PATH ====================="
    hdfs_cmd dfs -du -h /agri || true
    echo
    echo "============ BLOCKS + REPLICATION (raw daily) =========="
    # -files -blocks shows the block list; without it fsck only prints
    # a health summary and the replication story is invisible.
    hdfs_cmd fsck /agri/raw/daily_market_prices -files -blocks 2>/dev/null | tail -25 || true
    ;;

  down)
    $COMPOSE down
    ;;

  destroy)
    echo "This DELETES all data stored in HDFS (raw copies and processed)."
    read -r -p "Type 'destroy' to confirm: " reply
    [ "$reply" = "destroy" ] || { echo "aborted"; exit 1; }
    $COMPOSE down -v
    ;;

  *)
    echo "usage: $0 {up|load|report|down|destroy}"
    exit 1
    ;;
esac
