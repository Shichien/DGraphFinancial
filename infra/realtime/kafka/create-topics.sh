#!/usr/bin/env bash
set -euo pipefail

for i in {1..60}; do
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list >/dev/null 2>&1 && break
  sleep 2
done

topics=(
  transactions.raw
  transactions.cleaned
  features.realtime
  risk.scored
  risk.alerts
  risk.audit
  devices.raw
  accounts.raw
  blacklist.raw
  labels.delayed
)

for topic in "${topics[@]}"; do
  /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:9092 \
    --create \
    --if-not-exists \
    --topic "$topic" \
    --partitions 3 \
    --replication-factor 1
done
