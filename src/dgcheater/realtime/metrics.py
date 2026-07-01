from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RuntimeMetrics:
    started_at: float
    updated_at: float
    produced_events: int = 0
    feature_events: int = 0
    scored_events: int = 0
    alert_events: int = 0
    last_event_timestamp: int = 0
    scoring_latency_ms_avg: float = 0.0
    scoring_latency_ms_max: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeMetricsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("output/realtime/runtime-metrics.json")

    def load(self) -> RuntimeMetrics:
        if not self.path.exists():
            now = time.time()
            return RuntimeMetrics(started_at=now, updated_at=now)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            now = time.time()
            return RuntimeMetrics(started_at=now, updated_at=now)
        return RuntimeMetrics(**data)

    def save(self, metrics: RuntimeMetrics) -> None:
        metrics.updated_at = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        try:
            temp_path.write_text(json.dumps(metrics.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(self.path)
        except OSError:
            temp_path.unlink(missing_ok=True)

    def record_produced(self, count: int = 1, event_timestamp: int = 0) -> None:
        metrics = self.load()
        metrics.produced_events += count
        metrics.last_event_timestamp = max(metrics.last_event_timestamp, event_timestamp)
        self.save(metrics)

    def record_feature(self, count: int = 1, event_timestamp: int = 0) -> None:
        metrics = self.load()
        metrics.feature_events += count
        metrics.last_event_timestamp = max(metrics.last_event_timestamp, event_timestamp)
        self.save(metrics)

    def record_scored(self, latency_ms: float, is_alert: bool, event_timestamp: int = 0) -> None:
        metrics = self.load()
        previous = metrics.scored_events
        metrics.scored_events += 1
        metrics.alert_events += 1 if is_alert else 0
        metrics.last_event_timestamp = max(metrics.last_event_timestamp, event_timestamp)
        metrics.scoring_latency_ms_avg = (
            (metrics.scoring_latency_ms_avg * previous + latency_ms) / metrics.scored_events
            if metrics.scored_events
            else latency_ms
        )
        metrics.scoring_latency_ms_max = max(metrics.scoring_latency_ms_max, latency_ms)
        self.save(metrics)


def derive_dashboard_metrics(metrics: RuntimeMetrics) -> dict[str, Any]:
    now = time.time()
    elapsed = max(metrics.updated_at - metrics.started_at, 1.0)
    freshness = max(now - metrics.updated_at, 0.0)
    produced_rate = metrics.produced_events / elapsed
    feature_rate = metrics.feature_events / elapsed
    scored_rate = metrics.scored_events / elapsed
    return {
        "kafkaThroughput": round(produced_rate, 2),
        "featureThroughput": round(feature_rate, 2),
        "scoringThroughput": round(scored_rate, 2),
        "flinkLatencyMs": round(max(metrics.produced_events - metrics.feature_events, 0) / max(produced_rate, 1.0) * 1000, 2),
        "modelLatencyMs": round(metrics.scoring_latency_ms_avg, 2),
        "modelLatencyMsMax": round(metrics.scoring_latency_ms_max, 2),
        "scoredEvents": metrics.scored_events,
        "alertEvents": metrics.alert_events,
        "metricFreshnessSec": round(freshness, 2),
    }
