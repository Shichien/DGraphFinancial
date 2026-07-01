from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_sources import DATA_SOURCES, RealtimeDataSource, create_simulator, get_data_source
from .feature_engine import RealtimeFeatureEngine
from .graph_state import InMemoryGraphState
from .manual_console import ALIASES, ManualRiskSession, aggregate_summary
from .metrics import RuntimeMetricsStore, derive_dashboard_metrics
from .realtime_sinks import RedisRiskSink
from .schemas import RiskDecision
from .scoring import SCORE_WEIGHTS, FusionRiskScorer
from .simulator import DEMO_EVENT_COUNT, MultiSourceFraudSimulator
from .storage import RiskEventRepository


app = FastAPI(title="智鉴流盾实时反诈 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FRONTEND_DIST = _REPO_ROOT / "frontend" / "graph-stream" / "dist"
DEMO_BATCH_SIZE = 40
GRAPH_WINDOW_EVENT_LIMIT = 80
GRAPH_CUMULATIVE_EVENT_LIMIT = DEMO_EVENT_COUNT
GRAPH_NODE_LIMIT = 240
GRAPH_EDGE_LIMIT = 640
GRAPH_RELATED_NODE_LIMIT = 16
GRAPH_NEIGHBORHOOD_LIMIT = 80
if _FRONTEND_DIST.exists():
    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="graph-stream-assets")


@dataclass
class DemoRuntime:
    source: RealtimeDataSource = field(default_factory=lambda: get_data_source("kafka_live" if os.getenv("DG_DATABASE_URL") else "simulator"))
    simulator: MultiSourceFraudSimulator = field(init=False)
    graph: InMemoryGraphState = field(default_factory=InMemoryGraphState)
    engine: RealtimeFeatureEngine = field(init=False)
    scorer: FusionRiskScorer = field(default_factory=FusionRiskScorer)
    decisions: list[RiskDecision] = field(default_factory=list)
    event_total: int = 0
    event_limit: int = DEMO_EVENT_COUNT
    started_at: float = field(default_factory=time.time)
    last_advance_at: float = field(default_factory=time.time)
    scoring_latency_ms_avg: float = 0.0

    def __post_init__(self) -> None:
        self.simulator = create_simulator(self.source)
        self.engine = RealtimeFeatureEngine(self.graph)

    def advance(self, batch_size: int) -> None:
        for batch in self.simulator.multi_source_stream(batch_size):
            self.engine.ingest_account(batch.account)
            self.engine.ingest_device(batch.device)
            if batch.blacklist is not None:
                self.engine.ingest_blacklist(batch.blacklist)
            event = batch.transaction
            self.event_total += 1
            features = self.engine.transform(event)
            started = time.perf_counter()
            decision = self.scorer.score(features)
            latency_ms = (time.perf_counter() - started) * 1000
            previous = max(len(self.decisions), 0)
            self.scoring_latency_ms_avg = (
                (self.scoring_latency_ms_avg * previous + latency_ms) / (previous + 1)
                if previous >= 0
                else latency_ms
            )
            self.decisions.append(decision)
        self.last_advance_at = time.time()
        if len(self.decisions) > self.event_limit:
            del self.decisions[: len(self.decisions) - self.event_limit]

    def reset(self, source_key: str | None = None) -> None:
        if source_key is not None:
            self.source = get_data_source(source_key)
        self.simulator = create_simulator(self.source)
        self.graph = InMemoryGraphState()
        self.engine = RealtimeFeatureEngine(self.graph)
        self.decisions.clear()
        self.event_total = 0
        self.started_at = time.time()
        self.last_advance_at = self.started_at
        self.scoring_latency_ms_avg = 0.0


runtime: DemoRuntime | None = None
manual_runtime: ManualRiskSession | None = None


def _runtime() -> DemoRuntime:
    global runtime
    if runtime is None:
        from .dgraph_prior import DGraphAccountPrior

        DGraphAccountPrior.load(repo_root=_REPO_ROOT)
        runtime = DemoRuntime()
    return runtime


def _manual_runtime() -> ManualRiskSession:
    global manual_runtime
    if manual_runtime is None:
        manual_runtime = ManualRiskSession()
    return manual_runtime


def serve(host: str = "127.0.0.1", port: int = 8060, reload: bool = False) -> None:
    uvicorn.run("dgcheater.realtime.dashboard_api:app", host=host, port=port, reload=reload)


serve_app = typer.Typer(no_args_is_help=False)


@serve_app.callback(invoke_without_command=True)
def serve_command(
    host: str = "127.0.0.1",
    port: int = 8060,
    reload: bool = False,
) -> None:
    """Start the realtime dashboard API."""
    serve(host=host, port=port, reload=reload)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_model=None)
def dashboard_index():
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "ok", "message": "frontend dist not built"}


@app.get("/api/graph-stream")
def graph_stream(
    batch_size: int = Query(default=DEMO_BATCH_SIZE, ge=1, le=DEMO_EVENT_COUNT),
    view: str = Query(default="window", pattern="^(window|cumulative)$"),
) -> dict[str, Any]:
    demo_runtime = _runtime()
    repository = _repository() if demo_runtime.source.key == "kafka_live" else None
    if repository is not None:
        try:
            return _snapshot_from_database(repository, _redis_sink(), demo_runtime.source, view=view)
        except Exception:
            pass
    demo_runtime.advance(batch_size)
    return _snapshot_from_runtime(demo_runtime, view=view)


@app.post("/api/graph-stream/reset")
def reset_graph_stream(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    source_key = str((payload or {}).get("source") or "").strip() or None
    try:
        _runtime().reset(source_key)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "source": _runtime().source.key}


@app.get("/api/data-sources")
def data_sources() -> dict[str, Any]:
    current = _runtime().source.key
    return {
        "current": current,
        "sources": [
            {
                "key": item.key,
                "label": item.label,
                "description": item.description,
                "mode": item.mode,
                "active": item.key == current,
            }
            for item in DATA_SOURCES.values()
        ],
    }


@app.post("/api/data-source")
def switch_data_source(payload: dict[str, Any]) -> dict[str, Any]:
    source_key = str(payload.get("source") or "").strip()
    try:
        source = get_data_source(source_key)
        _runtime().reset(source.key)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "current": source.key,
        "source": {
            "key": source.key,
            "label": source.label,
            "description": source.description,
            "mode": source.mode,
        },
    }


@app.get("/api/risk-console/schema")
def risk_console_schema() -> dict[str, Any]:
    session = _manual_runtime()
    return {
        "aliases": ALIASES,
        "defaults": session.defaults,
        "state": _risk_console_state(session),
    }


@app.post("/api/risk-console/run")
def run_risk_console(payload: dict[str, Any]) -> dict[str, Any]:
    session = _manual_runtime()
    history_limit = int(payload.get("history_limit", 100))
    history_limit = max(0, min(history_limit, 500))
    try:
        if bool(payload.get("reset_before", False)):
            session.reset()
        commands = _risk_console_commands(payload)
        results: list[dict[str, Any]] = []
        for command in commands:
            results.extend(session.run_command(command))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    history = session.results[-history_limit:] if history_limit else []
    return {
        "ok": True,
        "results": results,
        "summary": aggregate_summary(results),
        "history": history,
        "historySummary": aggregate_summary(session.results),
        "state": _risk_console_state(session),
    }


@app.get("/api/graph-node-neighborhood")
def graph_node_neighborhood(
    node_id: int,
    scope: str = "full",
    limit: int = Query(default=GRAPH_NEIGHBORHOOD_LIMIT, ge=1, le=GRAPH_NODE_LIMIT),
) -> dict[str, Any]:
    repository = _repository()
    if repository is not None:
        try:
            return _neighborhood_from_repository(repository.node_neighborhood(node_id, limit=limit), scope, limit)
        except Exception:
            pass
    demo_runtime = _runtime()
    features = demo_runtime.graph.features(node_id, depth=2 if scope == "full" else 1, limit=limit)
    nodes = [
        {
            "id": item,
            "label": 1 if item in demo_runtime.graph.risky_nodes else 0,
            "degree": len(demo_runtime.graph.neighbors.get(item, set())),
            "eventCount": 0,
            "riskScore": 0.65 if item in demo_runtime.graph.risky_nodes else 0.18,
            "riskLevel": "high" if item in demo_runtime.graph.risky_nodes else "low",
            "action": "manual_review" if item in demo_runtime.graph.risky_nodes else "pass",
            "detectedFraud": item in demo_runtime.graph.risky_nodes,
            "groundTruth": "runtime",
            "timeSpan": 0,
            "amountMax": 0.0,
            "staticScore": 0.65 if item in demo_runtime.graph.risky_nodes else 0.18,
        }
        for item in [node_id, *features.related_nodes]
    ]
    edges = [
        {
            "id": f"runtime-{node_id}-{item}",
            "source": node_id,
            "target": item,
            "timestamp": 0,
            "riskLevel": "high" if item in demo_runtime.graph.risky_nodes or node_id in demo_runtime.graph.risky_nodes else "low",
            "riskScore": 0.65 if item in demo_runtime.graph.risky_nodes or node_id in demo_runtime.graph.risky_nodes else 0.18,
            "edgeType": 1,
            "channel": "runtime",
            "sourceScope": "full",
        }
        for item in features.related_nodes
        if item in demo_runtime.graph.neighbors.get(node_id, set())
    ]
    return {
        "available": True,
        "focusNode": node_id,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "scope": scope,
            "limit": limit,
            "totalIncidentEdges": len(edges),
            "totalNeighborCount": max(len(nodes) - 1, 0),
            "returnedEdges": len(edges),
            "returnedNodes": len(nodes),
            "truncated": len(nodes) >= limit,
        },
    }


@app.get("/api/audit-logs")
def audit_logs(limit: int = Query(default=60, ge=1, le=300)) -> dict[str, Any]:
    repository = _repository()
    if repository is None:
        return {"logs": []}
    try:
        return {"logs": repository.audit_logs(limit=limit)}
    except Exception:
        return {"logs": []}


@app.get("/api/case-actions")
def case_actions(limit: int = Query(default=60, ge=1, le=300)) -> dict[str, Any]:
    repository = _repository()
    if repository is None:
        return {"actions": []}
    try:
        return {"actions": repository.case_actions(limit=limit)}
    except Exception:
        return {"actions": []}


@app.post("/api/case-actions")
def record_case_action(payload: dict[str, Any]) -> dict[str, Any]:
    repository = _repository()
    if repository is None:
        raise HTTPException(status_code=503, detail="case action repository unavailable")
    event_id = int(payload.get("event_id", 0))
    status = str(payload.get("status", "")).strip()
    reviewer = str(payload.get("reviewer", "analyst")).strip() or "analyst"
    note = str(payload.get("note", "")).strip()
    if event_id <= 0:
        raise HTTPException(status_code=400, detail="event_id is required")
    if status not in {"pending_review", "confirmed_fraud", "false_positive", "manual_block", "released", "auto_pass"}:
        raise HTTPException(status_code=400, detail="invalid case status")
    return {"action": repository.record_case_action(event_id=event_id, status=status, reviewer=reviewer, note=note)}


@app.get("/graph/node/{node_id}/features")
def graph_node_features(node_id: int) -> dict[str, Any]:
    features = _runtime().graph.features(node_id)
    return {
        "node_id": node_id,
        "neighbor_count": features.neighbor_count,
        "risky_neighbor_count": features.risky_neighbor_count,
        "component_size": features.component_size,
        "community_id": features.community_id,
        "related_nodes": features.related_nodes,
    }


@app.get("/graph/node/{node_id}/neighbors")
def graph_node_neighbors(node_id: int, limit: int = Query(default=GRAPH_NEIGHBORHOOD_LIMIT, ge=1, le=GRAPH_NODE_LIMIT)) -> dict[str, Any]:
    return graph_node_neighborhood(node_id=node_id, scope="full", limit=limit)


@app.get("/graph/community/{community_id}")
def graph_community(community_id: str) -> dict[str, Any]:
    nodes: list[int] = []
    for decision in _runtime().decisions:
        if decision.community_id == community_id:
            nodes.extend(decision.related_nodes or [decision.src_account, decision.dst_account])
    unique_nodes = sorted(set(nodes))
    return {"community_id": community_id, "nodes": unique_nodes, "size": len(unique_nodes)}


@app.get("/{path_name:path}", response_model=None)
def dashboard_fallback(path_name: str):
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "ok", "message": "frontend dist not built", "path": path_name}


def _repository() -> RiskEventRepository | None:
    database_url = os.getenv("DG_DATABASE_URL", "")
    if not database_url:
        return None
    return RiskEventRepository(database_url)


def _redis_sink() -> RedisRiskSink | None:
    redis_url = os.getenv("DG_REDIS_URL", "")
    if not redis_url:
        return None
    return RedisRiskSink(redis_url)


def _risk_console_commands(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reserved = {"reset_before", "history_limit"}
    commands = payload.get("commands", payload.get("command"))
    if commands is None:
        commands = {key: value for key, value in payload.items() if key not in reserved}
    if isinstance(commands, dict):
        return [commands]
    if isinstance(commands, list) and all(isinstance(item, dict) for item in commands):
        return commands
    raise ValueError("commands must be an object or an object list")


def _risk_console_state(session: ManualRiskSession) -> dict[str, Any]:
    return {
        "next_event_id": session.next_event_id,
        "next_timestamp": session.next_timestamp,
        "result_count": len(session.results),
    }


def _snapshot_from_database(
    repository: RiskEventRepository,
    redis_sink: RedisRiskSink | None = None,
    source: RealtimeDataSource | None = None,
    view: str = "window",
) -> dict[str, Any]:
    graph_limit = _graph_event_limit(view)
    raw = repository.dashboard_snapshot(limit=graph_limit)
    events = [_event_from_db(row) for row in raw["events"]]
    level_counts = _level_counts_from_events(events)
    nodes = _nodes_from_events(events)
    edges = _edges_from_events(events)
    fraud_scripts = _fraud_scripts_from_rows(raw.get("fraud_scripts", []), events)
    redis_snapshot = _read_redis_snapshot(redis_sink)
    top_nodes = redis_snapshot.get("top_risk_nodes") or [
        {
            "id": int(row["node_id"]),
            "riskScore": float(row["risk_score"]),
            "riskLevel": _level(float(row["risk_score"])),
            "degree": 1,
            "eventCount": int(row["event_count"]),
            "staticScore": float(row["risk_score"]),
            "detectedFraud": float(row["risk_score"]) >= 0.50,
            "groundTruth": "runtime",
        }
        for row in raw["top_nodes"]
    ]
    return {
        "meta": {
            "dataset": source.label if source is not None else "Kafka 实时链路",
            "sourceKey": source.key if source is not None else "kafka_live",
            "sourceDescription": source.description if source is not None else "读取 Kafka、Flink、评分服务写入的风险事件库。",
            "mode": source.mode if source is not None else "Kafka 实时链路",
            "position": min(raw["total_events"], DEMO_EVENT_COUNT),
            "totalEvents": min(max(raw["total_events"], len(events)), DEMO_EVENT_COUNT),
            "progress": min(raw["total_events"] / DEMO_EVENT_COUNT, 1.0) if raw["total_events"] else 0.0,
            "eventsPerSecond": 0.0,
            "currentTimestamp": events[0]["timestamp"] if events else 0,
            "windowSize": len(events),
            "view": view,
            "graphWindowLimit": graph_limit,
            "complete": False,
        },
        "summary": _summary(level_counts, len(events), len(nodes), len(edges), len(events)),
        "topNodes": top_nodes,
        "recentEvents": events,
        "lastEvent": events[0] if events else None,
        "nodes": nodes,
        "edges": edges,
        "fraudScripts": fraud_scripts,
        "redis": redis_snapshot,
        "streamMetrics": _metrics_from_store(),
    }


def _snapshot_from_runtime(source: DemoRuntime, view: str = "window") -> dict[str, Any]:
    graph_limit = _graph_event_limit(view)
    recent = source.decisions[-graph_limit:]
    level_counts: dict[str, int] = {}
    for decision in source.decisions:
        level_counts[decision.risk_level] = level_counts.get(decision.risk_level, 0) + 1
    node_scores: dict[int, dict[str, float]] = {}
    for decision in source.decisions:
        item = node_scores.setdefault(decision.src_account, {"risk": 0.0, "eventCount": 0.0})
        item["risk"] = max(item["risk"], decision.risk_score)
        item["eventCount"] += 1
    top_nodes = [
        {"id": node_id, "risk": values["risk"], "eventCount": int(values["eventCount"])}
        for node_id, values in sorted(node_scores.items(), key=lambda item: (-item[1]["risk"], -item[1]["eventCount"]))[:20]
    ]
    events = [_event_from_decision(decision) for decision in reversed(recent)]
    nodes = _nodes_from_events(events)
    edges = _edges_from_events(events)
    fraud_scripts = _fraud_scripts_from_events(events)
    return {
        "meta": {
            "dataset": source.source.label,
            "sourceKey": source.source.key,
            "sourceDescription": source.source.description,
            "mode": source.source.mode,
            "position": min(source.event_total, source.event_limit),
            "totalEvents": source.event_limit,
            "progress": min(source.event_total / source.event_limit, 1.0) if source.event_limit else 1.0,
            "eventsPerSecond": 0.0,
            "currentTimestamp": events[0]["timestamp"] if events else 0,
            "windowSize": len(events),
            "view": view,
            "graphWindowLimit": graph_limit,
            "complete": False,
        },
        "summary": _summary(level_counts, len(source.decisions), len(nodes), len(edges), len(events)),
        "topNodes": top_nodes,
        "recentEvents": events,
        "lastEvent": events[0] if events else None,
        "nodes": nodes,
        "edges": edges,
        "fraudScripts": fraud_scripts,
        "streamMetrics": _metrics_from_runtime(source),
    }


def _graph_event_limit(view: str) -> int:
    return GRAPH_CUMULATIVE_EVENT_LIMIT if view == "cumulative" else GRAPH_WINDOW_EVENT_LIMIT


def _level_counts_from_events(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        level = str(event.get("riskLevel") or "low")
        counts[level] = counts.get(level, 0) + 1
    return counts


def _summary(level_counts: dict[str, int], total: int, node_count: int, edge_count: int, window_count: int) -> dict[str, Any]:
    high = int(level_counts.get("high", 0))
    critical = int(level_counts.get("critical", 0))
    medium = int(level_counts.get("medium", 0))
    low = int(level_counts.get("low", 0))
    return {
        "total": total,
        "visibleNodeCount": node_count,
        "visibleEdgeCount": edge_count,
        "windowEventCount": window_count,
        "activeNodeCount": node_count,
        "detectedFraudNodeCount": high + critical,
        "criticalCount": critical,
        "highCount": high,
        "mediumCount": medium,
        "lowCount": low,
        "low": low,
        "medium": medium,
        "high": high,
        "critical": critical,
        "alertCount": high + critical,
        "riskRate": round((high + critical) / total, 4) if total else 0.0,
    }


def _metrics_from_store() -> dict[str, Any]:
    try:
        return derive_dashboard_metrics(RuntimeMetricsStore().load())
    except Exception:
        return {
            "kafkaThroughput": 0.0,
            "featureThroughput": 0.0,
            "scoringThroughput": 0.0,
            "flinkLatencyMs": 0.0,
            "modelLatencyMs": 0.0,
            "modelLatencyMsMax": 0.0,
            "scoredEvents": 0,
            "alertEvents": 0,
            "metricFreshnessSec": 0.0,
        }


def _metrics_from_runtime(source: DemoRuntime) -> dict[str, Any]:
    elapsed = max(source.last_advance_at - source.started_at, 1.0)
    throughput = source.event_total / elapsed
    return {
        "kafkaThroughput": round(throughput, 2),
        "featureThroughput": round(throughput, 2),
        "scoringThroughput": round(throughput, 2),
        "flinkLatencyMs": 0.0,
        "modelLatencyMs": round(source.scoring_latency_ms_avg, 2),
        "modelLatencyMsMax": round(source.scoring_latency_ms_avg, 2),
        "scoredEvents": len(source.decisions),
        "alertEvents": sum(1 for item in source.decisions if item.risk_level in {"critical", "high"}),
        "metricFreshnessSec": round(max(time.time() - source.last_advance_at, 0.0), 2),
    }


def _event_from_decision(decision: RiskDecision) -> dict[str, Any]:
    amount = float(decision.evidence.get("amount", 0.0))
    channel = str(decision.evidence.get("source_channel", "unknown"))
    related_nodes = decision.related_nodes[:GRAPH_RELATED_NODE_LIMIT]
    return {
        "eventId": decision.event_id,
        "timestamp": decision.timestamp,
        "srcNode": decision.src_account,
        "dstNode": decision.dst_account,
        "edgeType": 1,
        "channel": channel,
        "amount": amount,
        "riskScore": decision.risk_score,
        "riskLevel": decision.risk_level,
        "action": decision.decision,
        "focusNode": decision.src_account,
        "focusDegree": int(decision.evidence.get("graph_neighbor_count", 1)),
        "focusNodeDetail": _node_detail(
            node_id=decision.src_account,
            risk_score=decision.risk_score,
            risk_level=decision.risk_level,
            action=decision.decision,
            amount=amount,
            evidence=decision.evidence,
        ),
        "reasonCodes": decision.reason_codes,
        "evidence": decision.evidence,
        "communityId": decision.community_id,
        "relatedNodes": related_nodes,
        "isFraudEdge": 1 if decision.risk_level in {"critical", "high"} else 0,
    }


def _event_from_db(row: dict[str, Any]) -> dict[str, Any]:
    evidence = row["evidence_json"]
    if isinstance(evidence, str):
        import json

        evidence = json.loads(evidence)
    risk_score = float(row["risk_score"])
    risk_level = str(row["risk_level"])
    amount = float(evidence.get("amount", 0.0)) if isinstance(evidence, dict) else 0.0
    src_account = int(row["src_account"])
    dst_account = int(row["dst_account"])
    reason_codes = [str(item) for item in row.get("reason_codes", [])]
    related_edges = (row.get("related_edges", []) or [])[:GRAPH_RELATED_NODE_LIMIT]
    related_nodes = [int(item) for item in row.get("related_nodes", [])]
    if not related_nodes:
        related_nodes = [src_account, dst_account]
    else:
        related_nodes = [
            src_account,
            dst_account,
            *sorted(set(related_nodes) - {src_account, dst_account}),
        ][:GRAPH_RELATED_NODE_LIMIT]
    return {
        "eventId": int(row["event_id"]),
        "timestamp": int(row["event_time"]),
        "srcNode": src_account,
        "dstNode": dst_account,
        "edgeType": 1,
        "channel": evidence.get("source_channel", "unknown") if isinstance(evidence, dict) else "unknown",
        "amount": amount,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "action": str(row["decision"]),
        "focusNode": src_account,
        "focusDegree": int(evidence.get("graph_neighbor_count", 1)) if isinstance(evidence, dict) else 1,
        "focusNodeDetail": _node_detail(
            node_id=src_account,
            risk_score=risk_score,
            risk_level=risk_level,
            action=str(row["decision"]),
            amount=amount,
            evidence=evidence if isinstance(evidence, dict) else {},
        ),
        "reasonCodes": reason_codes,
        "evidence": evidence if isinstance(evidence, dict) else {},
        "communityId": str(row["community_id"]),
        "relatedNodes": related_nodes,
        "relatedEdges": related_edges,
        "isFraudEdge": 1 if risk_level in {"critical", "high"} else 0,
    }


def _fraud_scripts_from_rows(rows: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if rows:
        return [
            {
                "type": str(row.get("fraud_script_type") or "unknown"),
                "count": int(row.get("count") or 0),
                "maxRiskScore": float(row.get("max_risk_score") or 0.0),
                "avgRiskScore": float(row.get("avg_risk_score") or 0.0),
            }
            for row in rows
        ]
    return _fraud_scripts_from_events(events)


def _fraud_scripts_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, float]] = {}
    for event in events:
        evidence = event.get("evidence") or {}
        if not isinstance(evidence, dict):
            continue
        fraud_type = str(evidence.get("fraud_script_type") or "none")
        if fraud_type == "none":
            continue
        item = stats.setdefault(fraud_type, {"count": 0.0, "riskSum": 0.0, "maxRiskScore": 0.0})
        risk_score = float(event.get("riskScore") or 0.0)
        item["count"] += 1
        item["riskSum"] += risk_score
        item["maxRiskScore"] = max(item["maxRiskScore"], risk_score)
    result = []
    for fraud_type, item in stats.items():
        count = int(item["count"])
        result.append(
            {
                "type": fraud_type,
                "count": count,
                "maxRiskScore": item["maxRiskScore"],
                "avgRiskScore": item["riskSum"] / count if count else 0.0,
            }
        )
    return sorted(result, key=lambda item: (-item["count"], -item["maxRiskScore"], item["type"]))[:12]


def _read_redis_snapshot(redis_sink: RedisRiskSink | None) -> dict[str, Any]:
    if redis_sink is None:
        return {}
    try:
        snapshot = redis_sink.snapshot()
    except Exception:
        return {}
    return {
        "top_risk_nodes": [
            {
                "id": int(item["node_id"]),
                "riskScore": float(item["risk_score"]),
                "riskLevel": _level(float(item["risk_score"])),
                "degree": 1,
                "eventCount": 1,
                "staticScore": float(item["risk_score"]),
                "detectedFraud": float(item["risk_score"]) >= 0.50,
                "groundTruth": "runtime",
            }
            for item in snapshot.get("top_risk_nodes", [])
        ],
        "community_risk_rank": snapshot.get("community_risk_rank", []),
        "recent_alerts": snapshot.get("recent_alerts", []),
    }


def _neighborhood_from_repository(raw: dict[str, Any], scope: str, limit: int) -> dict[str, Any]:
    raw_nodes = [int(item["id"]) for item in raw.get("nodes", [])]
    raw_edges = raw.get("edges", [])
    nodes = [
        {
            "id": node_id,
            "label": 0,
            "degree": 1,
            "eventCount": 0,
            "riskScore": 0.5 if node_id == int(raw["node_id"]) else 0.28,
            "riskLevel": "high" if node_id == int(raw["node_id"]) else "low",
            "action": "manual_review" if node_id == int(raw["node_id"]) else "pass",
            "detectedFraud": node_id == int(raw["node_id"]),
            "groundTruth": "runtime",
            "timeSpan": 0,
            "amountMax": 0.0,
            "staticScore": 0.5 if node_id == int(raw["node_id"]) else 0.28,
        }
        for node_id in raw_nodes
    ]
    edges = [
        {
            "id": f"db-{edge['event_id']}-{edge['src_account']}-{edge['dst_account']}",
            "source": int(edge["src_account"]),
            "target": int(edge["dst_account"]),
            "timestamp": int(edge["event_id"]),
            "riskLevel": "high",
            "riskScore": 0.5,
            "edgeType": 1,
            "channel": str(edge["relation_type"]),
            "sourceScope": "full",
        }
        for edge in raw_edges
    ]
    return {
        "available": True,
        "focusNode": int(raw["node_id"]),
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "scope": scope,
            "limit": limit,
            "totalIncidentEdges": len(edges),
            "totalNeighborCount": max(len(nodes) - 1, 0),
            "returnedEdges": len(edges),
            "returnedNodes": len(nodes),
            "truncated": len(nodes) >= limit,
        },
    }


def _nodes_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: dict[int, dict[str, Any]] = {}
    degree: dict[int, set[int]] = {}
    for event in events:
        src = int(event["srcNode"])
        dst = int(event["dstNode"])
        degree.setdefault(src, set()).add(dst)
        degree.setdefault(dst, set()).add(src)
        related_nodes = [int(item) for item in event.get("relatedNodes", [])]
        for related in related_nodes:
            if related != src:
                degree.setdefault(src, set()).add(related)
                degree.setdefault(related, set()).add(src)
        for node_id in sorted(set([src, dst, *related_nodes])):
            current = nodes.get(node_id)
            if node_id == src:
                risk_score = float(event["riskScore"])
            elif node_id == dst:
                risk_score = max(float(event["riskScore"]) * 0.72, 0.02)
            else:
                risk_score = max(float(event["riskScore"]) * 0.56, 0.02)
            if current is None or risk_score > current["riskScore"]:
                nodes[node_id] = {
                    "id": node_id,
                    "label": 1 if event["riskLevel"] in {"critical", "high"} else 0,
                    "degree": 1,
                    "eventCount": 0,
                    "riskScore": risk_score,
                    "riskLevel": _level(risk_score),
                    "action": event["action"],
                    "detectedFraud": risk_score >= 0.50,
                    "groundTruth": "runtime",
                    "timeSpan": 0,
                    "amountMax": float(event.get("amount", 0.0)),
                    "staticScore": risk_score,
                }
            nodes[node_id]["eventCount"] += 1
            nodes[node_id]["amountMax"] = max(nodes[node_id]["amountMax"], float(event.get("amount", 0.0)))
    for node_id, neighbors in degree.items():
        if node_id in nodes:
            nodes[node_id]["degree"] = len(neighbors)
    return sorted(nodes.values(), key=lambda item: item["riskScore"], reverse=True)[:GRAPH_NODE_LIMIT]


def _edges_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_edge(edge: dict[str, Any]) -> bool:
        edge_id = str(edge["id"])
        if edge_id in seen:
            return True
        if len(edges) >= GRAPH_EDGE_LIMIT:
            return False
        seen.add(edge_id)
        edges.append(edge)
        return len(edges) < GRAPH_EDGE_LIMIT

    for event in events:
        if not append_edge({
            "id": f"rt-{event['eventId']}",
            "source": int(event["srcNode"]),
            "target": int(event["dstNode"]),
            "timestamp": int(event["timestamp"]),
            "riskLevel": event["riskLevel"],
            "riskScore": float(event["riskScore"]),
            "edgeType": int(event.get("edgeType", 1)),
            "channel": event.get("channel", "unknown"),
            "sourceScope": "runtime",
        }):
            return edges

    for event in events:
        related_edges = event.get("relatedEdges") or []
        if related_edges:
            for index, relation in enumerate(related_edges[:GRAPH_RELATED_NODE_LIMIT]):
                source = int(relation.get("src_account", event["srcNode"]))
                target = int(relation.get("dst_account", event["dstNode"]))
                edge_id = f"rel-{event['eventId']}-{source}-{target}-{index}"
                if not append_edge({
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "timestamp": int(event["timestamp"]),
                    "riskLevel": event["riskLevel"],
                    "riskScore": float(event["riskScore"]),
                    "edgeType": int(event.get("edgeType", 1)),
                    "channel": relation.get("relation_type", "related_node"),
                    "sourceScope": "related",
                }):
                    return edges
            continue
        for target in sorted(set(int(item) for item in event.get("relatedNodes", [])))[:GRAPH_RELATED_NODE_LIMIT]:
            source = int(event["srcNode"])
            if target in {source, int(event["dstNode"])}:
                continue
            edge_id = f"rel-{event['eventId']}-{source}-{target}"
            if not append_edge({
                "id": edge_id,
                "source": source,
                "target": target,
                "timestamp": int(event["timestamp"]),
                "riskLevel": event["riskLevel"],
                "riskScore": float(event["riskScore"]),
                "edgeType": int(event.get("edgeType", 1)),
                "channel": "related_node",
                "sourceScope": "related",
            }):
                return edges
    return edges


def _node_detail(
    *,
    node_id: int,
    risk_score: float,
    risk_level: str,
    action: str,
    amount: float,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    components = [
        ("offline_model_score", "离线模型先验", SCORE_WEIGHTS["offline_model_score"], evidence.get("offline_model_score", 0.0)),
        ("realtime_behavior_score", "实时行为风险", SCORE_WEIGHTS["realtime_behavior_score"], evidence.get("realtime_behavior_score", 0.0)),
        ("graph_community_score", "图团伙风险", SCORE_WEIGHTS["graph_community_score"], evidence.get("graph_community_score", 0.0)),
        ("rule_score", "规则命中风险", SCORE_WEIGHTS["rule_score"], evidence.get("rule_score", 0.0)),
    ]
    return {
        "id": node_id,
        "label": 1 if risk_level in {"critical", "high"} else 0,
        "degree": int(evidence.get("graph_neighbor_count", 1)),
        "eventCount": 1,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "action": action,
        "detectedFraud": risk_level in {"critical", "high"},
        "groundTruth": "runtime",
        "timeSpan": 1,
        "amountMax": amount,
        "staticScore": float(evidence.get("offline_model_score", risk_score)),
        "scoreBreakdown": {
            "finalScore": risk_score,
            "riskLevel": risk_level,
            "action": action,
            "formula": "综合风险分由离线模型先验、实时交易行为、图团伙风险和规则命中加权得到。",
            "metrics": {
                "degree": int(evidence.get("graph_neighbor_count", 1)),
                "eventCount": 1,
                "timeSpan": 1,
                "channelCount": 1,
                "edgeTypeCount": 1,
                "amountMax": amount,
            },
            "components": [
                {
                    "key": key,
                    "label": label,
                    "value": float(value),
                    "weight": weight,
                    "evidence": label,
                    "contribution": float(value) * weight,
                }
                for key, label, weight, value in components
            ],
        },
    }


def _level(score: float) -> str:
    if score >= 0.78:
        return "critical"
    if score >= 0.50:
        return "high"
    if score >= 0.30:
        return "medium"
    return "low"
