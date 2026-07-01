from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..core.config import APP_CONFIG
from ..dgraph.data import DGraphRawData
from .prototype import OnlineRiskScorer, build_transaction_stream, risk_level_from_score


@dataclass(slots=True)
class DynamicGraphConfig:
    event_count: int = 5_000
    window_size: int = 900
    replay_interval_ms: int = 180
    seed: int = APP_CONFIG.training.seed


class DynamicGraphDetector:
    def __init__(
        self,
        raw: DGraphRawData,
        dataset_key: str,
        output_dir: Path,
        config: DynamicGraphConfig,
    ) -> None:
        self.raw = raw
        self.dataset_key = dataset_key
        self.output_dir = output_dir
        self.config = config
        self.stream = build_transaction_stream(raw, event_count=config.event_count, seed=config.seed)
        self.stream = self.stream.sort_values(["timestamp", "event_id"], kind="mergesort").reset_index(drop=True)
        self.scorer = OnlineRiskScorer(raw, dataset_key=dataset_key, output_dir=output_dir)
        self.static_scores = self._score_static_nodes(self.stream)
        self.global_stream_risk_prior = self._stream_risk_prior(self.stream)
        self.channel_risk_prior = self._build_category_risk_prior(self.stream, "channel")
        self.edge_type_risk_prior = self._build_category_risk_prior(self.stream, "edge_type")
        self.full_incident_edges = self._build_full_incident_edges()
        self.position = 0
        self.started_at = time.time()
        self.last_tick_at = self.started_at
        self.ingested_edges: deque[dict[str, Any]] = deque(maxlen=config.window_size)
        self.recent_events: deque[dict[str, Any]] = deque(maxlen=36)
        self.adjacency: dict[int, set[int]] = defaultdict(set)
        self.node_state: dict[int, dict[str, Any]] = {}
        self.edge_type_counts: dict[int, int] = defaultdict(int)
        self.channel_counts: dict[str, int] = defaultdict(int)
        self.risk_counts: dict[str, int] = defaultdict(int)
        self.detected_fraud_nodes: set[int] = set()
        self.last_event: dict[str, Any] | None = None

    def reset(self) -> dict[str, Any]:
        self.position = 0
        self.started_at = time.time()
        self.last_tick_at = self.started_at
        self.ingested_edges.clear()
        self.recent_events.clear()
        self.adjacency.clear()
        self.node_state.clear()
        self.edge_type_counts.clear()
        self.channel_counts.clear()
        self.risk_counts.clear()
        self.detected_fraud_nodes.clear()
        self.last_event = None
        return {"status": "ok", "position": self.position, "totalEvents": int(len(self.stream))}

    def tick(self, max_events: int = 1) -> None:
        now = time.time()
        interval = max(self.config.replay_interval_ms / 1_000.0, 0.001)
        elapsed = max(now - self.last_tick_at, 0.0)
        if elapsed < interval and self.position > 0:
            return
        event_quota = min(max_events, max(1, int(elapsed / interval) if self.position > 0 else 1))
        for _ in range(event_quota):
            if self.position >= len(self.stream):
                break
            row = self.stream.iloc[self.position]
            self.position += 1
            self.last_tick_at = now
            self._ingest_row(row)

    def snapshot(self) -> dict[str, Any]:
        self.tick(max_events=8)
        nodes = self._visible_nodes()
        edges = self._visible_edges(nodes)
        window_node_ids = self._window_node_ids()
        window_summary = self._window_summary(window_node_ids)
        top_nodes = sorted(
            (self.node_state[node] for node in window_node_ids if node in self.node_state),
            key=lambda item: (float(item["risk_score"]), int(item["degree"]), int(item["last_timestamp"])),
            reverse=True,
        )[:12]
        elapsed = max(time.time() - self.started_at, 1e-6)
        total_events = max(len(self.stream), 1)
        progress = self.position / total_events
        return {
            "meta": {
                "dataset": "DGraph-Fin",
                "mode": "按边时间戳逐条回放",
                "position": self.position,
                "totalEvents": int(len(self.stream)),
                "progress": progress,
                "eventsPerSecond": self.position / elapsed,
                "currentTimestamp": int(self.last_event["timestamp"]) if self.last_event else None,
                "windowSize": self.config.window_size,
                "complete": self.position >= len(self.stream),
            },
            "summary": {
                "visibleNodeCount": len(nodes),
                "visibleEdgeCount": len(edges),
                **window_summary,
            },
            "lastEvent": self.last_event,
            "nodes": nodes,
            "edges": edges,
            "topNodes": [self._node_payload(item) for item in top_nodes],
            "recentEvents": list(self.recent_events),
            "channels": self._counter_payload(self.channel_counts),
            "edgeTypes": self._counter_payload(self.edge_type_counts),
        }

    def node_neighborhood(self, node_id: int, limit: int = 80, scope: str = "full") -> dict[str, Any]:
        if node_id < 0 or node_id >= self.raw.num_nodes:
            return {
                "available": False,
                "reason": "node_not_found",
                "focusNode": node_id,
                "nodes": [],
                "edges": [],
                "meta": {"scope": scope, "limit": limit, "totalIncidentEdges": 0, "truncated": False},
            }
        edge_indices = self._incident_edge_indices(node_id, scope=scope)
        total_incident_edges = len(edge_indices)
        selected_edges = self._rank_incident_edges(edge_indices, limit=limit)
        selected_nodes = {node_id}
        edges: list[dict[str, Any]] = []
        for edge_idx in selected_edges:
            src = int(self.raw.edge_index[edge_idx, 0])
            dst = int(self.raw.edge_index[edge_idx, 1])
            selected_nodes.add(src)
            selected_nodes.add(dst)
            edge_score = max(self._node_display_score(src), self._node_display_score(dst))
            risk_level, _ = risk_level_from_score(edge_score)
            edges.append(
                {
                    "id": f"full-{int(edge_idx)}",
                    "source": src,
                    "target": dst,
                    "timestamp": int(self.raw.edge_timestamp[edge_idx]),
                    "riskLevel": risk_level,
                    "riskScore": edge_score,
                    "edgeType": int(self.raw.edge_type[edge_idx]),
                    "channel": self._channel_for_edge(int(self.raw.edge_type[edge_idx]), int(self.raw.edge_timestamp[edge_idx])),
                    "sourceScope": scope,
                }
            )
        nodes = [self._neighborhood_node_payload(node) for node in selected_nodes]
        nodes.sort(key=lambda item: (item["id"] != node_id, -float(item["riskScore"]), -int(item["degree"]), int(item["id"])))
        return {
            "available": True,
            "focusNode": node_id,
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "scope": scope,
                "limit": limit,
                "totalIncidentEdges": total_incident_edges,
                "returnedEdges": len(edges),
                "returnedNodes": len(nodes),
                "truncated": total_incident_edges > len(edges),
            },
        }

    def _score_static_nodes(self, stream: pd.DataFrame) -> dict[int, float]:
        nodes = np.unique(stream[["src_node", "dst_node"]].to_numpy(dtype=np.int64).reshape(-1))
        probe_frame = pd.DataFrame(
            {
                "event_id": np.arange(nodes.shape[0], dtype=np.int64),
                "timestamp": np.zeros(nodes.shape[0], dtype=np.int32),
                "src_node": nodes,
                "dst_node": nodes,
                "edge_type": np.zeros(nodes.shape[0], dtype=np.int32),
                "channel": np.full(nodes.shape[0], "node_probe", dtype=object),
                "amount": np.ones(nodes.shape[0], dtype=np.float64),
                "device_fingerprint": [f"probe_{int(node)}" for node in nodes],
                "is_fraud_edge": np.full(nodes.shape[0], -1, dtype=np.int32),
            }
        )
        risk_frame, _ = self.scorer.score_frame(probe_frame)
        score_by_node: dict[int, float] = {}
        for row in risk_frame.itertuples(index=False):
            score_by_node[int(row.src_node)] = float(row.src_node_score)
        return score_by_node

    @staticmethod
    def _stream_risk_prior(stream: pd.DataFrame) -> float:
        labels = stream["is_fraud_edge"].to_numpy(dtype=np.float64)
        labels = labels[labels >= 0]
        if labels.size == 0:
            return 0.0
        return float(np.clip(labels.mean(), 0.0, 1.0))

    def _build_category_risk_prior(self, stream: pd.DataFrame, column: str) -> dict[Any, float]:
        base_rate = self.global_stream_risk_prior
        denominator = max(base_rate * 1.8, 0.02)
        valid = stream[stream["is_fraud_edge"] >= 0]
        grouped = valid.groupby(column, sort=False)["is_fraud_edge"].agg(["sum", "count"])
        priors: dict[Any, float] = {}
        for key, row in grouped.iterrows():
            smoothed_rate = (float(row["sum"]) + base_rate * 8.0) / (float(row["count"]) + 8.0)
            priors[key] = self._clamp01(smoothed_rate / denominator)
        return priors

    def _build_full_incident_edges(self) -> dict[int, np.ndarray]:
        endpoints = self.raw.edge_index.reshape(-1).astype(np.int64)
        edge_ids = np.repeat(np.arange(self.raw.edge_index.shape[0], dtype=np.int64), 2)
        order = np.argsort(endpoints, kind="mergesort")
        sorted_nodes = endpoints[order]
        sorted_edges = edge_ids[order]
        incident: dict[int, np.ndarray] = {}
        if sorted_nodes.size == 0:
            return incident
        unique_nodes, starts = np.unique(sorted_nodes, return_index=True)
        ends = np.r_[starts[1:], sorted_nodes.size]
        for node, start, end in zip(unique_nodes, starts, ends):
            incident[int(node)] = sorted_edges[start:end]
        return incident

    def _incident_edge_indices(self, node_id: int, scope: str) -> list[int]:
        if scope == "window":
            edge_ids: list[int] = []
            for edge in self.ingested_edges:
                if int(edge["source"]) == node_id or int(edge["target"]) == node_id:
                    edge_id = str(edge["id"]).removeprefix("e-")
                    if edge_id.isdigit():
                        edge_ids.append(int(edge_id))
            return edge_ids
        return [int(edge_idx) for edge_idx in self.full_incident_edges.get(node_id, np.array([], dtype=np.int64))]

    def _rank_incident_edges(self, edge_indices: list[int], limit: int) -> list[int]:
        if not edge_indices:
            return []
        unique_edges = np.array(sorted(set(edge_indices)), dtype=np.int64)
        src = self.raw.edge_index[unique_edges, 0]
        dst = self.raw.edge_index[unique_edges, 1]
        src_scores = np.array([self._node_display_score(int(node)) for node in src], dtype=np.float64)
        dst_scores = np.array([self._node_display_score(int(node)) for node in dst], dtype=np.float64)
        risk_scores = np.maximum(src_scores, dst_scores)
        timestamps = self.raw.edge_timestamp[unique_edges].astype(np.int64)
        order = np.lexsort((-unique_edges, -timestamps, -risk_scores))
        ranked = unique_edges[order]
        return [int(edge_idx) for edge_idx in ranked[: max(1, limit)]]

    def _neighborhood_node_payload(self, node_id: int) -> dict[str, Any]:
        state = self.node_state.get(node_id)
        if state is not None:
            return self._node_payload(state)
        risk_score = float(self.static_scores.get(node_id, 0.0))
        risk_level, action = risk_level_from_score(risk_score)
        label = int(self.raw.y[node_id])
        degree = int(len(self.full_incident_edges.get(node_id, np.array([], dtype=np.int64))))
        return {
            "id": int(node_id),
            "label": label,
            "degree": degree,
            "eventCount": 0,
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "action": action,
            "detectedFraud": risk_level in {"critical", "high"},
            "groundTruth": "fraud" if label == 1 else "normal" if label == 0 else "background",
            "timeSpan": 0,
            "amountMax": 0.0,
            "staticScore": risk_score,
        }

    def _node_display_score(self, node_id: int) -> float:
        state = self.node_state.get(node_id)
        if state is not None:
            return float(state["risk_score"])
        return float(self.static_scores.get(node_id, 0.0))

    @staticmethod
    def _channel_for_edge(edge_type: int, timestamp: int) -> str:
        channels = ("wallet", "bank_app", "qr_pay", "web", "merchant_api")
        return channels[(edge_type + timestamp) % len(channels)]

    def _ingest_row(self, row: pd.Series) -> None:
        src = int(row["src_node"])
        dst = int(row["dst_node"])
        timestamp = int(row["timestamp"])
        edge_type = int(row["edge_type"])
        channel = str(row["channel"])
        amount = float(row["amount"])
        self.adjacency[src].add(dst)
        self.adjacency[dst].add(src)
        self.edge_type_counts[edge_type] += 1
        self.channel_counts[channel] += 1
        src_state = self._update_node(src, dst, timestamp, edge_type, channel, amount)
        dst_state = self._update_node(dst, src, timestamp, edge_type, channel, amount)
        focus = src_state if float(src_state["risk_score"]) >= float(dst_state["risk_score"]) else dst_state
        risk_score = max(float(src_state["risk_score"]), float(dst_state["risk_score"]))
        risk_level, action = risk_level_from_score(risk_score)
        self.risk_counts[risk_level] += 1
        if risk_level in {"critical", "high"}:
            self.detected_fraud_nodes.add(int(focus["node_id"]))
        event = {
            "eventId": int(row["event_id"]),
            "timestamp": timestamp,
            "srcNode": src,
            "dstNode": dst,
            "edgeType": edge_type,
            "channel": channel,
            "amount": amount,
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "action": action,
            "focusNode": int(focus["node_id"]),
            "focusDegree": int(focus["degree"]),
            "focusNodeDetail": self._node_payload(focus, include_breakdown=True),
            "isFraudEdge": int(row.get("is_fraud_edge", -1)),
        }
        self.last_event = event
        self.recent_events.appendleft(event)
        self.ingested_edges.append(
            {
                "id": f"e-{int(row['event_id'])}",
                "source": src,
                "target": dst,
                "timestamp": timestamp,
                "riskLevel": risk_level,
                "riskScore": risk_score,
                "edgeType": edge_type,
                "channel": channel,
            }
        )

    def _update_node(
        self,
        node: int,
        neighbor: int,
        timestamp: int,
        edge_type: int,
        channel: str,
        amount: float,
    ) -> dict[str, Any]:
        state = self.node_state.get(node)
        if state is None:
            label = int(self.raw.y[node])
            state = {
                "node_id": node,
                "label": label,
                "degree": 0,
                "event_count": 0,
                "first_timestamp": timestamp,
                "last_timestamp": timestamp,
                "amount_sum": 0.0,
                "amount_max": 0.0,
                "neighbors": set(),
                "edge_types": defaultdict(int),
                "channels": defaultdict(int),
                "static_score": float(self.static_scores.get(node, 0.0)),
                "neighbor_risk_max": 0.0,
                "channel_prior_max": 0.0,
                "edge_type_prior_max": 0.0,
                "risk_score": 0.0,
            }
            self.node_state[node] = state
        state["event_count"] = int(state["event_count"]) + 1
        state["last_timestamp"] = max(int(state["last_timestamp"]), timestamp)
        state["first_timestamp"] = min(int(state["first_timestamp"]), timestamp)
        state["amount_sum"] = float(state["amount_sum"]) + amount
        state["amount_max"] = max(float(state["amount_max"]), amount)
        state["neighbors"].add(neighbor)
        state["degree"] = len(state["neighbors"])
        state["edge_types"][edge_type] += 1
        state["channels"][channel] += 1
        state["neighbor_risk_max"] = max(float(state["neighbor_risk_max"]), float(self.static_scores.get(neighbor, 0.0)))
        state["channel_prior_max"] = max(
            float(state["channel_prior_max"]),
            float(self.channel_risk_prior.get(channel, self.global_stream_risk_prior)),
        )
        state["edge_type_prior_max"] = max(
            float(state["edge_type_prior_max"]),
            float(self.edge_type_risk_prior.get(edge_type, self.global_stream_risk_prior)),
        )
        state["risk_score"] = self._dynamic_risk_score(state)
        return state

    def _dynamic_risk_score(self, state: dict[str, Any]) -> float:
        breakdown = self._score_breakdown(state)
        return float(breakdown["finalScore"])

    def _score_breakdown(self, state: dict[str, Any]) -> dict[str, Any]:
        static_score = float(state["static_score"])
        degree = int(state["degree"])
        event_count = int(state["event_count"])
        time_span = max(int(state["last_timestamp"]) - int(state["first_timestamp"]), 1)
        max_amount_pressure = min(math.log1p(float(state["amount_max"])) / math.log1p(200_000), 1.0)
        neighbor_pressure = float(state.get("neighbor_risk_max", 0.0))
        channel_prior_pressure = float(state.get("channel_prior_max", self.global_stream_risk_prior))
        edge_type_prior_pressure = float(state.get("edge_type_prior_max", self.global_stream_risk_prior))
        degree_pressure = self._clamp01((1.0 - math.exp(-degree / 12.0)) * 0.55 + neighbor_pressure * 0.45)
        burst_rate = self._clamp01(
            (1.0 - math.exp(-event_count / 4.0)) * 0.45
            + (1.0 / (1.0 + time_span / 8.0)) * 0.30
            + max_amount_pressure * 0.25
        )
        channel_pressure = self._clamp01(min(len(state["channels"]) / 5.0, 1.0) * 0.45 + channel_prior_pressure * 0.55)
        type_pressure = self._clamp01(min(len(state["edge_types"]) / 11.0, 1.0) * 0.45 + edge_type_prior_pressure * 0.55)
        components = [
            {
                "key": "staticScore",
                "label": "静态模型先验",
                "value": static_score,
                "weight": 0.58,
                "evidence": "由离线图模型给出的节点基础风险",
            },
            {
                "key": "degreePressure",
                "label": "关系风险压力",
                "value": degree_pressure,
                "weight": 0.16,
                "evidence": f"当前窗口关联 {degree} 个邻居，邻居最高静态风险 {neighbor_pressure:.4f}",
            },
            {
                "key": "burstRate",
                "label": "突发交易强度",
                "value": burst_rate,
                "weight": 0.10,
                "evidence": f"{event_count} 次交易覆盖 {time_span} 个时间刻度，最大金额压力 {max_amount_pressure:.4f}",
            },
            {
                "key": "channelPressure",
                "label": "渠道风险压力",
                "value": channel_pressure,
                "weight": 0.08,
                "evidence": f"出现 {len(state['channels'])} 类交易渠道，渠道历史风险 {channel_prior_pressure:.4f}",
            },
            {
                "key": "typePressure",
                "label": "交易类型压力",
                "value": type_pressure,
                "weight": 0.05,
                "evidence": f"出现 {len(state['edge_types'])} 类交易关系，类型历史风险 {edge_type_prior_pressure:.4f}",
            },
            {
                "key": "amountPressure",
                "label": "金额压力",
                "value": max_amount_pressure,
                "weight": 0.03,
                "evidence": f"最大交易金额 {float(state['amount_max']):.2f}",
            },
        ]
        raw_score = sum(float(item["value"]) * float(item["weight"]) for item in components)
        final_score = min(max(raw_score, 0.0), 1.0)
        risk_level, action = risk_level_from_score(final_score)
        for item in components:
            item["contribution"] = float(item["value"]) * float(item["weight"])
        return {
            "finalScore": final_score,
            "riskLevel": risk_level,
            "action": action,
            "formula": "综合风险分由静态模型先验、关系风险压力、突发交易强度、渠道风险压力、交易类型压力和金额压力加权得到。条形表示该项特征强度，数字表示加权后的得分贡献。",
            "metrics": {
                "degree": degree,
                "eventCount": event_count,
                "timeSpan": time_span,
                "channelCount": len(state["channels"]),
                "edgeTypeCount": len(state["edge_types"]),
                "amountMax": float(state["amount_max"]),
            },
            "components": components,
        }

    def _visible_nodes(self) -> list[dict[str, Any]]:
        edge_nodes = self._window_node_ids()
        ranked = sorted(
            (self.node_state[node] for node in edge_nodes if node in self.node_state),
            key=lambda item: (float(item["risk_score"]), int(item["last_timestamp"])),
            reverse=True,
        )
        max_visible_nodes = 320
        selected_ids = [int(item["node_id"]) for item in ranked[:110]]
        selected_set = set(selected_ids)
        for edge in reversed(self.ingested_edges):
            for endpoint in (int(edge["source"]), int(edge["target"])):
                if endpoint not in selected_set and endpoint in self.node_state:
                    selected_ids.append(endpoint)
                    selected_set.add(endpoint)
                    if len(selected_ids) >= max_visible_nodes:
                        break
            if len(selected_ids) >= max_visible_nodes:
                break
        selected = [self.node_state[node_id] for node_id in selected_ids if node_id in self.node_state]
        return [self._node_payload(item) for item in selected]

    def _visible_edges(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        visible_ids = {int(node["id"]) for node in nodes}
        edges = [
            edge
            for edge in self.ingested_edges
            if int(edge["source"]) in visible_ids and int(edge["target"]) in visible_ids
        ]
        return edges[-620:]

    def _window_node_ids(self) -> set[int]:
        node_ids: set[int] = set()
        for edge in self.ingested_edges:
            node_ids.add(int(edge["source"]))
            node_ids.add(int(edge["target"]))
        return node_ids

    def _window_summary(self, node_ids: set[int]) -> dict[str, int]:
        level_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for edge in self.ingested_edges:
            level = str(edge["riskLevel"])
            if level in level_counts:
                level_counts[level] += 1
        detected_nodes = sum(
            1
            for node in node_ids
            if node in self.node_state
            and self._node_risk_level(self.node_state[node]) in {"critical", "high"}
        )
        return {
            "windowEventCount": len(self.ingested_edges),
            "activeNodeCount": len(node_ids),
            "detectedFraudNodeCount": detected_nodes,
            "criticalCount": level_counts["critical"],
            "highCount": level_counts["high"],
            "mediumCount": level_counts["medium"],
            "lowCount": level_counts["low"],
        }

    def _node_payload(self, state: dict[str, Any], include_breakdown: bool = False) -> dict[str, Any]:
        risk_score = float(state["risk_score"])
        risk_level, action = risk_level_from_score(risk_score)
        label = int(state["label"])
        payload = {
            "id": int(state["node_id"]),
            "label": label,
            "degree": int(state["degree"]),
            "eventCount": int(state["event_count"]),
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "action": action,
            "detectedFraud": risk_level in {"critical", "high"},
            "groundTruth": "fraud" if label == 1 else "normal" if label == 0 else "background",
            "timeSpan": int(state["last_timestamp"]) - int(state["first_timestamp"]),
            "amountMax": float(state["amount_max"]),
            "staticScore": float(state["static_score"]),
        }
        if include_breakdown:
            payload["scoreBreakdown"] = self._score_breakdown(state)
        return payload

    @staticmethod
    def _node_risk_level(state: dict[str, Any]) -> str:
        risk_level, _ = risk_level_from_score(float(state["risk_score"]))
        return risk_level

    @staticmethod
    def _clamp01(value: float) -> float:
        return min(max(float(value), 0.0), 1.0)

    @staticmethod
    def _counter_payload(counter: dict[Any, int], limit: int = 8) -> list[dict[str, Any]]:
        items = sorted(counter.items(), key=lambda item: item[1], reverse=True)[:limit]
        return [{"label": str(label), "value": int(value)} for label, value in items]
