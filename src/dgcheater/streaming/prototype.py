from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time
import warnings

import joblib
import numpy as np
import pandas as pd

from ..core.config import APP_CONFIG
from ..dgraph.data import DGraphRawData
from ..dgraph.features import FeatureBundle, build_features, build_features_for_nodes, feature_cache_path, get_or_create_feature_cache
from ..models.training import _build_known_label_neighbor_features


RISK_LEVELS = APP_CONFIG.risk_levels


@dataclass(slots=True)
class StreamingPrototypeResult:
    stream_path: str
    risk_events_path: str
    trace_summary_path: str
    performance_json_path: str
    performance_md_path: str
    event_count: int
    scored_node_count: int
    throughput_events_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    high_or_above_events: int


class OnlineRiskScorer:
    """Reusable micro-batch scorer for replay, API service and Flink sink workers."""

    def __init__(self, raw: DGraphRawData, dataset_key: str, output_dir: Path) -> None:
        self.raw = raw
        self.dataset_key = dataset_key
        self.output_dir = output_dir
        self.full_bundle: FeatureBundle | None = None
        self.full_label_neighbor_features: np.ndarray | None = None
        if APP_CONFIG.training.use_cached_features:
            cache_file = feature_cache_path(APP_CONFIG.paths.cache_dir, dataset_key)
            if cache_file.exists():
                self.full_bundle = get_or_create_feature_cache(raw, APP_CONFIG.paths.cache_dir, cache_key=dataset_key)
        elif raw.num_nodes <= 250_000:
            self.full_bundle = build_features(raw)

        if self.full_bundle is not None:
            self.feature_names = self.full_bundle.feature_names
            self.features = self.full_bundle.features
            self.full_label_neighbor_features = _build_known_label_neighbor_features(raw.edge_index, raw.train_idx, raw.y, raw.num_nodes)
        else:
            preview_bundle = build_features_for_nodes(raw, np.array([0], dtype=np.int64))
            self.feature_names = preview_bundle.feature_names
            self.features = None

        model_dir = output_dir / dataset_key / "models"
        self.xgb_model = joblib.load(model_dir / "xgboost.joblib")
        self.lgb_model = joblib.load(model_dir / "lightgbm_aux.joblib")

    def score_frame(self, stream_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
        scored_nodes = np.unique(stream_frame[["src_node", "dst_node"]].to_numpy(dtype=np.int64).reshape(-1))
        if self.full_bundle is None:
            node_bundle = build_features_for_nodes(self.raw, scored_nodes)
            node_label_features = _build_label_neighbor_features_for_nodes(
                self.raw.edge_index,
                self.raw.train_idx,
                self.raw.y,
                self.raw.num_nodes,
                scored_nodes,
            )
            feature_matrix = node_bundle.features
            score_matrix = np.concatenate([feature_matrix, node_label_features], axis=1)
            node_explanations = _build_node_explanations(self.feature_names, feature_matrix, scored_nodes, local_rows=True)
        else:
            feature_matrix = self.full_bundle.features[scored_nodes]
            score_matrix = np.concatenate([feature_matrix, self.full_label_neighbor_features[scored_nodes]], axis=1)
            node_explanations = _build_node_explanations(self.feature_names, feature_matrix, scored_nodes, local_rows=True)

        start_total = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            xgb_prob = self.xgb_model.predict_proba(score_matrix)[:, 1]
            lgb_prob = self.lgb_model.predict_proba(score_matrix)[:, 1]
        blend = APP_CONFIG.models.graph.blend
        blended_prob = blend.xgboost_weight * xgb_prob + blend.lightgbm_weight * lgb_prob
        score_seconds = max(time.perf_counter() - start_total, 1e-9)
        node_scores = {
            int(node): float(score)
            for node, score in zip(scored_nodes.tolist(), blended_prob.tolist(), strict=True)
        }

        risk_rows: list[dict[str, object]] = []
        for row in stream_frame.itertuples(index=False):
            src_score = node_scores[int(row.src_node)]
            dst_score = node_scores[int(row.dst_node)]
            amount_boost = min(float(row.amount) / 200_000.0, 1.0) * 0.05
            edge_score = min(max(src_score, dst_score) + amount_boost, 1.0)
            risk_level, action = risk_level_from_score(edge_score)
            focus_node = int(row.src_node if src_score >= dst_score else row.dst_node)
            risk_rows.append(
                {
                    "event_id": int(row.event_id),
                    "timestamp": int(row.timestamp),
                    "src_node": int(row.src_node),
                    "dst_node": int(row.dst_node),
                    "edge_type": int(row.edge_type),
                    "channel": row.channel,
                    "amount": float(row.amount),
                    "device_fingerprint": row.device_fingerprint,
                    "risk_score": edge_score,
                    "risk_level": risk_level,
                    "action": action,
                    "focus_node": focus_node,
                    "src_node_score": src_score,
                    "dst_node_score": dst_score,
                    "is_fraud_edge": int(row.is_fraud_edge) if hasattr(row, "is_fraud_edge") else -1,
                    "explanation": node_explanations.get(focus_node, f"score={edge_score:.4f}"),
                }
            )

        total_seconds = max(time.perf_counter() - start_total, 1e-9)
        per_node_latency_ms = (score_seconds / max(scored_nodes.shape[0], 1)) * 1_000
        latency_array = np.full(scored_nodes.shape[0], per_node_latency_ms, dtype=np.float64)
        risk_frame = pd.DataFrame(risk_rows)
        metrics = {
            "event_count": int(stream_frame.shape[0]),
            "scored_node_count": int(scored_nodes.shape[0]),
            "total_seconds": total_seconds,
            "score_seconds": score_seconds,
            "throughput_events_per_second": float(stream_frame.shape[0] / total_seconds),
            "throughput_scored_nodes_per_second": float(scored_nodes.shape[0] / total_seconds),
            "score_throughput_nodes_per_second": float(scored_nodes.shape[0] / score_seconds),
            "avg_latency_ms": float(latency_array.mean()) if latency_array.size else 0.0,
            "p50_latency_ms": float(np.percentile(latency_array, 50)) if latency_array.size else 0.0,
            "p95_latency_ms": float(np.percentile(latency_array, 95)) if latency_array.size else 0.0,
            "p99_latency_ms": float(np.percentile(latency_array, 99)) if latency_array.size else 0.0,
            "avg_event_end_to_end_ms": (total_seconds / max(stream_frame.shape[0], 1)) * 1_000,
        }
        return risk_frame, metrics


def risk_level_from_score(score: float) -> tuple[str, str]:
    for risk_level in RISK_LEVELS:
        if score >= risk_level.threshold:
            return risk_level.level, risk_level.action
    return "low", "pass"


def build_transaction_stream(
    raw: DGraphRawData,
    event_count: int,
    seed: int = APP_CONFIG.training.seed,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    edge_count = raw.edge_index.shape[0]
    sample_size = min(event_count, edge_count)
    sampled_edges = rng.choice(edge_count, size=sample_size, replace=False)
    sampled_edges = sampled_edges[np.argsort(raw.edge_timestamp[sampled_edges], kind="mergesort")]

    src = raw.edge_index[sampled_edges, 0].astype(np.int64)
    dst = raw.edge_index[sampled_edges, 1].astype(np.int64)
    edge_type = raw.edge_type[sampled_edges].astype(np.int32)
    timestamp = raw.edge_timestamp[sampled_edges].astype(np.int32)
    src_label = raw.y[src].astype(np.int32)
    dst_label = raw.y[dst].astype(np.int32)

    # These fields are simulator-side enrichments for the赛题要求中的跨渠道、设备指纹和金额维度。
    channels = np.array(["wallet", "bank_app", "qr_pay", "web", "merchant_api"], dtype=object)
    channel = channels[(edge_type + timestamp) % len(channels)]
    amount = rng.lognormal(mean=3.2 + (edge_type % 5) * 0.08, sigma=0.9, size=sample_size)
    amount = np.round(np.clip(amount, 1.0, 200_000.0), 2)
    device_hash = ((src * 1_315_423_911 + dst * 2_654_435_761 + edge_type * 97) % 1_000_003).astype(np.int64)

    return pd.DataFrame(
        {
            "event_id": np.arange(sample_size, dtype=np.int64),
            "timestamp": timestamp,
            "src_node": src,
            "dst_node": dst,
            "edge_type": edge_type,
            "channel": channel,
            "amount": amount,
            "device_fingerprint": [f"dev_{value:06d}" for value in device_hash],
            "src_label": src_label,
            "dst_label": dst_label,
            "is_fraud_edge": ((src_label == 1) | (dst_label == 1)).astype(np.int32),
        }
    )


def run_streaming_prototype(
    raw: DGraphRawData,
    dataset_key: str,
    output_dir: Path,
    event_count: int = APP_CONFIG.streaming.prototype.event_count,
    trace_top_k: int = APP_CONFIG.streaming.prototype.trace_top_k,
    seed: int = APP_CONFIG.training.seed,
) -> StreamingPrototypeResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stream_dir = output_dir / "streaming"
    stream_dir.mkdir(parents=True, exist_ok=True)

    stream_frame = build_transaction_stream(raw, event_count=event_count, seed=seed)
    stream_path = stream_dir / "transaction_stream_sample.csv"
    stream_frame.to_csv(stream_path, index=False, encoding="utf-8")

    scorer = OnlineRiskScorer(raw, dataset_key=dataset_key, output_dir=output_dir)
    risk_frame, scoring_metrics = scorer.score_frame(stream_frame)
    risk_events_path = stream_dir / "risk_events.csv"
    risk_frame.to_csv(risk_events_path, index=False, encoding="utf-8")

    trace_summary = build_ring_trace_summary(raw, risk_frame, top_k=trace_top_k)
    trace_summary_path = stream_dir / "ring_trace_summary.json"
    trace_summary_path.write_text(json.dumps(trace_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    performance = {
        "dataset": dataset_key,
        **scoring_metrics,
        "high_or_above_events": int(risk_frame["risk_level"].isin(["high", "critical"]).sum()),
        "risk_level_counts": {
            str(level): int(count)
            for level, count in risk_frame["risk_level"].value_counts().sort_index().items()
        },
    }
    performance_json_path = stream_dir / "performance_report.json"
    performance_json_path.write_text(json.dumps(performance, ensure_ascii=False, indent=2), encoding="utf-8")
    performance_md_path = stream_dir / "performance_report.md"
    performance_md_path.write_text(_build_performance_markdown(performance), encoding="utf-8")

    return StreamingPrototypeResult(
        stream_path=str(stream_path),
        risk_events_path=str(risk_events_path),
        trace_summary_path=str(trace_summary_path),
        performance_json_path=str(performance_json_path),
        performance_md_path=str(performance_md_path),
        event_count=performance["event_count"],
        scored_node_count=performance["scored_node_count"],
        throughput_events_per_second=performance["throughput_events_per_second"],
        avg_latency_ms=performance["avg_latency_ms"],
        p95_latency_ms=performance["p95_latency_ms"],
        p99_latency_ms=performance["p99_latency_ms"],
        high_or_above_events=performance["high_or_above_events"],
    )


def _build_node_explanations(
    feature_names: list[str],
    features: np.ndarray,
    nodes: np.ndarray,
    local_rows: bool = False,
) -> dict[int, str]:
    name_to_idx = {name: idx for idx, name in enumerate(feature_names)}
    total_degree_idx = name_to_idx.get("total_degree")
    time_span_idx = name_to_idx.get("timestamp_span")
    type_total_indices = [
        (int(name.removeprefix("edge_type_").removesuffix("_total")), idx)
        for name, idx in name_to_idx.items()
        if name.startswith("edge_type_") and name.endswith("_total")
    ]
    type_total_indices.sort(key=lambda item: item[0])

    explanations: dict[int, str] = {}
    for row_idx, node in enumerate(nodes.tolist()):
        row = features[row_idx] if local_rows else features[int(node)]
        total_degree = int(row[total_degree_idx]) if total_degree_idx is not None else 0
        time_span = int(row[time_span_idx]) if time_span_idx is not None else 0
        if type_total_indices:
            type_counts = np.asarray([row[idx] for _, idx in type_total_indices], dtype=np.float32)
            dominant_pos = int(type_counts.argmax())
            dominant_type = type_total_indices[dominant_pos][0]
            dominant_count = float(type_counts[dominant_pos])
            dominant_share = dominant_count / max(float(type_counts.sum()), 1.0)
        else:
            dominant_type = -1
            dominant_share = 0.0
        explanations[int(node)] = (
            f"degree={total_degree}; dominant_edge_type={dominant_type}; "
            f"dominant_share={dominant_share:.2f}; time_span={time_span}"
        )
    return explanations


def _build_label_neighbor_features_for_nodes(
    edge_index: np.ndarray,
    known_nodes: np.ndarray,
    y: np.ndarray,
    num_nodes: int,
    nodes: np.ndarray,
) -> np.ndarray:
    full = _build_known_label_neighbor_features(edge_index, known_nodes, y, num_nodes)
    return full[nodes]


def build_ring_trace_summary(raw: DGraphRawData, risk_frame: pd.DataFrame, top_k: int = 20) -> dict[str, object]:
    high_frame = risk_frame[risk_frame["risk_level"].isin(["high", "critical"])].copy()
    if high_frame.empty:
        high_frame = risk_frame.sort_values("risk_score", ascending=False).head(top_k).copy()
    else:
        high_frame = high_frame.sort_values("risk_score", ascending=False).head(top_k).copy()

    traces = []
    src_all = raw.edge_index[:, 0]
    dst_all = raw.edge_index[:, 1]
    for row in high_frame.itertuples(index=False):
        focus_node = int(row.focus_node)
        incident_mask = (src_all == focus_node) | (dst_all == focus_node)
        incident_edges = np.flatnonzero(incident_mask)
        neighbors = np.unique(raw.edge_index[incident_edges].reshape(-1))
        neighbors = neighbors[neighbors != focus_node]
        neighbor_labels = raw.y[neighbors]
        incident_types = raw.edge_type[incident_edges]
        incident_ts = raw.edge_timestamp[incident_edges]
        type_counts = np.bincount(incident_types) if incident_types.size else np.array([0])
        dominant_share = float(type_counts.max() / max(type_counts.sum(), 1))
        traces.append(
            {
                "event_id": int(row.event_id),
                "focus_node": focus_node,
                "risk_score": float(row.risk_score),
                "risk_level": row.risk_level,
                "neighbor_count": int(neighbors.shape[0]),
                "fraud_neighbor_count": int((neighbor_labels == 1).sum()),
                "normal_neighbor_count": int((neighbor_labels == 0).sum()),
                "background_neighbor_count": int(((neighbor_labels == 2) | (neighbor_labels == 3)).sum()),
                "incident_edge_count": int(incident_edges.shape[0]),
                "dominant_edge_type": int(type_counts.argmax()),
                "dominant_edge_type_share": dominant_share,
                "time_span": int(incident_ts.max() - incident_ts.min()) if incident_ts.size else 0,
            }
        )

    return {
        "summary": {
            "selected_event_count": len(traces),
            "selection_rule": "top high-or-critical risk events, falling back to top scores if none exist",
        },
        "traces": traces,
    }


def _build_performance_markdown(performance: dict[str, object]) -> str:
    risk_counts = performance["risk_level_counts"]
    risk_count_lines = "\n".join(f"- {level}: {count}" for level, count in risk_counts.items())
    return f"""# Streaming Prototype Performance

## Scope

- Dataset: `{performance["dataset"]}`
- Replayed events: `{performance["event_count"]}`
- Scored unique nodes: `{performance["scored_node_count"]}`

## Latency and Throughput

- Total runtime: `{performance["total_seconds"]:.4f}` seconds
- Model scoring runtime: `{performance["score_seconds"]:.4f}` seconds
- Event throughput: `{performance["throughput_events_per_second"]:.2f}` events/second
- Scored-node throughput: `{performance["throughput_scored_nodes_per_second"]:.2f}` nodes/second
- Pure scoring throughput: `{performance["score_throughput_nodes_per_second"]:.2f}` nodes/second
- Average node scoring latency: `{performance["avg_latency_ms"]:.4f}` ms
- P50 node scoring latency: `{performance["p50_latency_ms"]:.4f}` ms
- P95 node scoring latency: `{performance["p95_latency_ms"]:.4f}` ms
- P99 node scoring latency: `{performance["p99_latency_ms"]:.4f}` ms
- Average event end-to-end latency: `{performance["avg_event_end_to_end_ms"]:.4f}` ms

## Risk Level Distribution

{risk_count_lines}

## Interpretation

This is a single-machine replay prototype rather than a Kafka/Flink deployment. It gives the project a measured online-scoring baseline and a concrete path for replacing the CSV replay source with a streaming message queue.
"""


def result_to_json(result: StreamingPrototypeResult) -> str:
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)
