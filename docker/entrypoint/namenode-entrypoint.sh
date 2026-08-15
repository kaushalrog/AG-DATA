#!/usr/bin/env bash
# ---------------------------------------------------------------
# NameNode startup.
#
# Formats the filesystem only on first boot. Re-formatting an existing
# NameNode directory would generate a new namespace ID that the
# DataNodes reject, so the guard below is what makes `docker compose
# down` / `up` safe to repeat without losing HDFS.
# ---------------------------------------------------------------
set -euo pipefail

NAME_DIR="/hadoop/dfs/name"

if [ ! -d "${NAME_DIR}/current" ]; then
  echo "[namenode] empty name dir -> formatting new namespace"
  "${HADOOP_HOME}/bin/hdfs" namenode -format -force -nonInteractive
else
  echo "[namenode] existing namespace found -> skipping format"
fi

echo "[namenode] starting"
exec "${HADOOP_HOME}/bin/hdfs" namenode
