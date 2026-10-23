#!/usr/bin/env bash
# Run a job class from the assembly jar with spark-submit (local mode by default).
#   scripts/submit.sh com.agribigdata.forecast.ForecastPublish exp=fc_main_v3
# Build the jar first: sbt assembly.   MASTER=spark://host:7077 to target a cluster.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
CLASS="$1"; shift
exec spark-submit --master "${MASTER:-local[*]}" --driver-memory "${AGRI_DRIVER_MEMORY:-6g}" \
  --conf spark.driver.extraJavaOptions="--add-opens=java.base/sun.util.calendar=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED" \
  --conf spark.sql.shuffle.partitions="${AGRI_SHUFFLE_PARTITIONS:-64}" \
  --class "$CLASS" target/scala-2.13/agri-bigdata-assembly.jar "$@"
