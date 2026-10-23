#!/usr/bin/env bash
# Reproducible streaming demonstration on REAL archived records (replay, not live).
#
#   scripts/streaming_demo.sh [N_EVENTS] [RATE_PER_S] [ROOT]
#
# 1. starts the local Kafka broker (Homebrew, KRaft) and creates topics
# 2. starts PriceEventStream (bronze + silver + alerts) for a bounded time
# 3. replays N real reports from 2026-04-15..21 with labelled fault injection
#    (5% duplicates, 2% late, 1% invalid, local shuffling)
# 4. runs the batch/stream parity check
# Results: results/streaming/{batches.jsonl,progress.jsonl,parity.json,demo_summary.json}
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
N="${1:-20000}"; RATE="${2:-2000}"; ROOT="${3:-data/stream}"
BROKER="${AGRI_KAFKA_BOOTSTRAP:-localhost:9092}"
mkdir -p logs results/streaming
SENT=results/streaming/sent.ndjson; rm -f "$SENT"

if ! kafka-topics --bootstrap-server "$BROKER" --list >/dev/null 2>&1; then
  echo "==> starting Kafka"; brew services start kafka
  for _ in $(seq 1 30); do kafka-topics --bootstrap-server "$BROKER" --list >/dev/null 2>&1 && break; sleep 2; done
fi
for t in agri.prices.v1 agri.prices.dlq.v1; do
  kafka-topics --bootstrap-server "$BROKER" --create --if-not-exists --topic "$t" --partitions 6 --replication-factor 1 \
    --config retention.ms=1209600000 >/dev/null
done
kafka-topics --bootstrap-server "$BROKER" --describe --topic agri.prices.v1 | tee results/streaming/topic_describe.txt

RUN_SECONDS=$(( N / RATE + 150 ))
echo "==> starting stream job for ${RUN_SECONDS}s (root=$ROOT)"
scripts/submit.sh com.agribigdata.streaming.PriceEventStream bootstrap=$BROKER root=$ROOT runSeconds=$RUN_SECONDS startingOffsets=latest triggerSeconds=2 \
  > logs/stream_demo.log 2>&1 &
STREAM_PID=$!
# wait for the query to start before producing (startingOffsets=latest)
for _ in $(seq 1 90); do grep -q "Started\|\[STREAM\]\|batch_id" logs/stream_demo.log 2>/dev/null && break; [ -d "$ROOT/checkpoints/silver_prices/offsets" ] && break; sleep 2; done
sleep 10

echo "==> replaying $N real reports at $RATE/s with labelled faults"
PYTHONPATH=py .venv/bin/python -m agri.ingest.cli replay --start 2026-04-15 --end 2026-04-21 --limit "$N" \
  --duplicates 0.05 --late 0.02 --invalid 0.01 --shuffle 50 --bootstrap "$BROKER" --rate "$RATE" --ndjson "$SENT" \
  | tee results/streaming/producer_summary.json

echo "==> consumer lag right after producing"
kafka-consumer-groups --bootstrap-server "$BROKER" --list 2>/dev/null | head -5 || true
wait $STREAM_PID || true
grep -E '\[STREAM\]' logs/stream_demo.log | tail -3 || true

scripts/submit.sh com.agribigdata.streaming.StreamParityCheck root=$ROOT from=2026-04-15 to=2026-04-21 sent=$SENT 2>&1 | grep -E 'PARITY|Exception'
PYTHONPATH=py .venv/bin/python -m agri.analysis.stream_summary
