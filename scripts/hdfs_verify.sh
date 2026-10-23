#!/usr/bin/env bash
# HDFS data-lake + Spark-cluster verification. Every step's output is saved
# under results/hdfs/ as evidence.
#
#   scripts/hdfs_verify.sh
#
#  1. start HDFS (1 NN + 3 DN, replication 3) and the Spark standalone cluster
#  2. create the /agri layout (docs/ARCHITECTURE.md#hdfs-layout)
#  3. load silver 2025-2026, the gold layer and the selected models
#  4. fsck: block count, replication
#  5. run ScalabilityBench (W1, W2) on the Spark cluster, reading from HDFS
#  6. stop one DataNode, read the data back (must succeed), show under-replication,
#     restart it, wait for re-replication
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
OUT=results/hdfs; mkdir -p "$OUT"
COMPOSE="docker compose -f docker/docker-compose.yml ${SPARK_CLUSTER:+--profile spark}"
SPARK_CLUSTER="${SPARK_CLUSTER-1}"
NN="docker exec agri-namenode /opt/hadoop/bin/hdfs"
log() { echo "==> $*" | tee -a "$OUT/verify.log"; }

log "starting HDFS + Spark cluster"
$COMPOSE up -d 2>&1 | tail -3
for _ in $(seq 1 60); do $NN dfsadmin -safemode get 2>/dev/null | grep -q OFF && break; sleep 5; done
$NN dfsadmin -report 2>/dev/null | grep -E "Live datanodes|Configured Capacity|DFS Remaining" | tee "$OUT/report_before.txt"

log "creating layout"
$NN dfs -mkdir -p /agri/raw /agri/bronze /agri/silver /agri/features /agri/models /agri/predictions /agri/gold /agri/checkpoints /agri/metadata
log "loading silver 2025-2026, gold, models (staging mount is ../data -> /staging)"
$NN dfs -mkdir -p /agri/silver/daily_market_prices
for y in 2025 2026; do $NN dfs -put -f /staging/processed/daily_market_prices/year=$y /agri/silver/daily_market_prices/; done
[ -f data/gold/meta.json ] || { echo "data/gold/meta.json missing: run ForecastPublish first" >&2; exit 1; }
$NN dfs -rm -r -f /agri/gold >/dev/null 2>&1 || true
$NN dfs -put /staging/gold /agri/gold
EXP=$(python3 -c "import json;print(json.load(open('data/gold/meta.json'))['model_version'])")
$NN dfs -put -f "/staging/forecast/models/$EXP" /agri/models/
$NN dfs -du -h /agri | tee "$OUT/du.txt"
$NN fsck /agri/silver -files -blocks -replicaDetails 2>/dev/null | tail -20 | tee "$OUT/fsck_silver.txt"

JAR=target/scala-2.13/agri-bigdata-assembly.jar
[ -f "$JAR" ] || { log "building assembly jar"; sbt -batch assembly 2>&1 | grep -E "success|error" | tail -2; }
log "ScalabilityBench on spark://spark-master:7077 reading hdfs://namenode:9000"
docker exec agri-spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 \
  --class com.agribigdata.bench.ScalabilityBench --conf spark.executor.memory=2g --conf spark.executor.cores=3 \
  --conf spark.driver.host=spark-master --conf spark.sql.shuffle.partitions=32 \
  --driver-java-options "-Duser.dir=/opt/agri" \
  /opt/agri/$JAR mode=cores silver=hdfs://namenode:9000/agri/silver/daily_market_prices 2>&1 \
  | grep -E "\[SCALE\]|Exception|ERROR" | tee "$OUT/cluster_bench.txt" || true

log "failure test: stopping datanode2"
FILE=$($NN dfs -ls -R /agri/silver/daily_market_prices/year=2025 | awk '/parquet$/{print $8; exit}')
$NN dfs -checksum "$FILE" | tee "$OUT/checksum_before.txt"
docker stop agri-datanode2 >/dev/null
sleep 15
log "reading with a DataNode down"
$NN dfs -checksum "$FILE" | tee "$OUT/checksum_datanode_down.txt"
$NN dfs -cat "$FILE" | wc -c | tee "$OUT/read_bytes_datanode_down.txt"
$NN dfsadmin -report 2>/dev/null | grep -E "Live datanodes|Dead datanodes" | tee "$OUT/report_datanode_down.txt"
log "restarting datanode2"
docker start agri-datanode2 >/dev/null
sleep 40
$NN fsck /agri/silver 2>/dev/null | grep -E "Status|Under-replicated|Missing|Corrupt|Default replication|Average block replication" | tee "$OUT/fsck_after_restart.txt"
log "done; evidence in $OUT"
