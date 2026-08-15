#!/usr/bin/env bash
# ================================================================
# Kafka control for the simulated agricultural market stream.
#
# Kafka runs NATIVELY (Homebrew), not in Docker, so that container
# memory stays available for HDFS and Spark on this 16 GB machine.
# Modern Kafka uses KRaft, so there is no ZooKeeper here.
#
#   ./scripts/kafka_setup.sh up       start broker + create topic
#   ./scripts/kafka_setup.sh status   broker + topic description
#   ./scripts/kafka_setup.sh tail     watch live messages
#   ./scripts/kafka_setup.sh reset    delete and recreate the topic
#   ./scripts/kafka_setup.sh down     stop broker
# ================================================================
set -euo pipefail

cd "$( dirname "${BASH_SOURCE[0]}" )/.."
source scripts/env.sh

BROKER="localhost:9092"
TOPIC="agri-market-prices"

# Partitions: the unit of parallelism in Kafka. Six lets Spark
# Structured Streaming run up to six consuming tasks in parallel while
# staying comfortable on 10 local cores.
PARTITIONS=6

# Replication factor 1 — there is only one broker on this machine.
# This is a deliberate, stated limitation: Kafka replication cannot be
# demonstrated on a single-broker install, whereas HDFS replication can
# (and is) demonstrated on the 3-DataNode Docker cluster.
REPLICATION=1

case "${1:-up}" in

  up)
    if ! brew services list | grep -q "^kafka.*started"; then
      echo "==> starting Kafka broker"
      brew services start kafka
      echo "==> waiting for the broker to accept connections"
      for _ in $(seq 1 30); do
        if kafka-topics --bootstrap-server "$BROKER" --list >/dev/null 2>&1; then
          echo "    broker up"
          break
        fi
        sleep 2
      done
    else
      echo "==> broker already running"
    fi

    echo "==> creating topic '$TOPIC'"
    # --if-not-exists keeps this script idempotent.
    kafka-topics --bootstrap-server "$BROKER" \
      --create --if-not-exists \
      --topic "$TOPIC" \
      --partitions "$PARTITIONS" \
      --replication-factor "$REPLICATION"

    kafka-topics --bootstrap-server "$BROKER" --describe --topic "$TOPIC"
    ;;

  status)
    echo "==================== BROKER ===================="
    brew services list | grep kafka || echo "kafka service not found"
    echo
    echo "==================== TOPICS ===================="
    kafka-topics --bootstrap-server "$BROKER" --list
    echo
    kafka-topics --bootstrap-server "$BROKER" --describe --topic "$TOPIC" 2>/dev/null || true
    echo
    echo "============== END OFFSETS (message counts) ==============="
    # Sum of end offsets across partitions = messages produced so far.
    kafka-run-class kafka.tools.GetOffsetShell \
      --bootstrap-server "$BROKER" --topic "$TOPIC" 2>/dev/null || true
    ;;

  tail)
    echo "==> tailing '$TOPIC' (Ctrl-C to stop)"
    kafka-console-consumer --bootstrap-server "$BROKER" \
      --topic "$TOPIC" --from-beginning --max-messages "${2:-10}"
    ;;

  reset)
    echo "This deletes the topic and every message in it."
    read -r -p "Type 'reset' to confirm: " reply
    [ "$reply" = "reset" ] || { echo "aborted"; exit 1; }
    kafka-topics --bootstrap-server "$BROKER" --delete --topic "$TOPIC" || true
    sleep 3
    kafka-topics --bootstrap-server "$BROKER" \
      --create --topic "$TOPIC" \
      --partitions "$PARTITIONS" --replication-factor "$REPLICATION"
    ;;

  down)
    brew services stop kafka
    ;;

  *)
    echo "usage: $0 {up|status|tail|reset|down}"
    exit 1
    ;;
esac
