#!/usr/bin/env bash
# ---------------------------------------------------------------
# DataNode startup.
#
# Waits for the NameNode's RPC port before starting. Without this the
# DataNode exits on first connection refusal during a cold `up`, and
# the cluster comes up with fewer live nodes than configured — which
# would silently make replication=3 unachievable.
# ---------------------------------------------------------------
set -euo pipefail

echo "[datanode] waiting for namenode:9000"
for _ in $(seq 1 60); do
  if (echo > /dev/tcp/namenode/9000) >/dev/null 2>&1; then
    echo "[datanode] namenode is up"
    break
  fi
  sleep 2
done

echo "[datanode] starting"
exec "${HADOOP_HOME}/bin/hdfs" datanode
