#!/usr/bin/env bash
set -euo pipefail

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
export no_proxy="localhost,127.0.0.1,flink-jobmanager,kafka"
export NO_PROXY="${no_proxy}"

for i in {1..60}; do
  if curl -fsS http://flink-jobmanager:8081/overview >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

/opt/flink/bin/flink run \
  -m flink-jobmanager:8081 \
  -pyclientexec /usr/bin/python3 \
  -pyexec /usr/bin/python3 \
  -py /opt/dgcheater/jobs/realtime_features.py
