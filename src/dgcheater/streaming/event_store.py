from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd


SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS risk_events (
    event_id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    src_node INTEGER NOT NULL,
    dst_node INTEGER NOT NULL,
    edge_type INTEGER NOT NULL,
    channel TEXT NOT NULL,
    amount REAL NOT NULL,
    device_fingerprint TEXT NOT NULL,
    risk_score REAL NOT NULL,
    risk_level TEXT NOT NULL,
    action TEXT NOT NULL,
    focus_node INTEGER NOT NULL,
    src_node_score REAL NOT NULL,
    dst_node_score REAL NOT NULL,
    is_fraud_edge INTEGER NOT NULL DEFAULT -1,
    explanation TEXT NOT NULL,
    emitted_at INTEGER,
    status TEXT NOT NULL,
    review TEXT NOT NULL,
    trace_json TEXT NOT NULL DEFAULT '{}',
    audit_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_risk_events_level_score
ON risk_events (risk_level, risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_risk_events_created_at
ON risk_events (created_at DESC);
"""


POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS risk_events (
    event_id BIGINT PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    src_node BIGINT NOT NULL,
    dst_node BIGINT NOT NULL,
    edge_type INTEGER NOT NULL,
    channel TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    device_fingerprint TEXT NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_level TEXT NOT NULL,
    action TEXT NOT NULL,
    focus_node BIGINT NOT NULL,
    src_node_score DOUBLE PRECISION NOT NULL,
    dst_node_score DOUBLE PRECISION NOT NULL,
    is_fraud_edge INTEGER NOT NULL DEFAULT -1,
    explanation TEXT NOT NULL,
    emitted_at BIGINT,
    status TEXT NOT NULL,
    review TEXT NOT NULL,
    trace_json TEXT NOT NULL DEFAULT '{}',
    audit_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_risk_events_level_score
ON risk_events (risk_level, risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_risk_events_created_at
ON risk_events (created_at DESC);
"""


@dataclass(slots=True)
class EventStoreSummary:
    event_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


def default_sqlite_path(output_dir: Path) -> Path:
    return output_dir / "streaming" / "risk_events.sqlite"


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def resolve_database_url(database_url: str | None, output_dir: Path) -> str:
    return database_url or sqlite_url(default_sqlite_path(output_dir))


def _sqlite_path_from_url(database_url: str) -> Path:
    if not database_url.startswith("sqlite:///"):
        raise ValueError(f"不是 SQLite URL: {database_url}")
    return Path(database_url.removeprefix("sqlite:///"))


def _is_postgres_url(database_url: str) -> bool:
    scheme = urlparse(database_url).scheme
    return scheme in {"postgresql", "postgres"}


def _case_status(risk_level: str) -> str:
    if risk_level == "critical":
        return "冻结待复核"
    if risk_level == "high":
        return "人工复核中"
    if risk_level == "medium":
        return "二次验证"
    return "自动放行"


def _case_review(risk_level: str) -> str:
    if risk_level == "critical":
        return "建议立即冻结并核查同邻域账户"
    if risk_level == "high":
        return "建议人工复核交易链路和设备指纹"
    if risk_level == "medium":
        return "建议触发二次验证后再放行"
    return "暂未发现强风险信号"


class RiskEventStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.backend = "postgres" if _is_postgres_url(database_url) else "sqlite"
        self.path: Path | None = None
        if self.backend == "sqlite":
            self.path = _sqlite_path_from_url(database_url)
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        if self.backend == "postgres":
            import psycopg
            from psycopg.rows import dict_row

            return psycopg.connect(self.database_url, row_factory=dict_row)
        if self.path is None:
            raise RuntimeError("SQLite path is not initialized.")
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            if self.backend == "postgres":
                with connection.cursor() as cursor:
                    cursor.execute(POSTGRES_SCHEMA_SQL)
                connection.commit()
            else:
                connection.executescript(SQLITE_SCHEMA_SQL)

    def upsert_events(self, events: Iterable[dict[str, Any]]) -> int:
        rows = [normalize_risk_event(event) for event in events]
        if not rows:
            return 0
        self.init_schema()
        columns = list(rows[0].keys())
        placeholders = ", ".join("%s" if self.backend == "postgres" else "?" for _ in columns)
        assignments = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "event_id")
        sql = (
            f"INSERT INTO risk_events ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT(event_id) DO UPDATE SET {assignments}"
        )
        values = [tuple(row[column] for column in columns) for row in rows]
        with self.connect() as connection:
            if self.backend == "postgres":
                with connection.cursor() as cursor:
                    cursor.executemany(sql, values)
                connection.commit()
            else:
                connection.executemany(sql, values)
        return len(rows)

    def load_cases(self, limit: int = 12) -> list[dict[str, Any]]:
        self.init_schema()
        limit_placeholder = "%s" if self.backend == "postgres" else "?"
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM risk_events
                ORDER BY
                    CASE risk_level
                        WHEN 'critical' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        ELSE 3
                    END,
                    risk_score DESC,
                    event_id DESC
                LIMIT {limit_placeholder}
                """,
                (limit,),
            ).fetchall()
        return [row_to_case(row) for row in rows]

    def summary(self) -> EventStoreSummary:
        self.init_schema()
        with self.connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM risk_events").fetchone()[0])
            by_level = {
                str(row["risk_level"]): int(row["count"])
                for row in connection.execute("SELECT risk_level, COUNT(*) AS count FROM risk_events GROUP BY risk_level")
            }
        return EventStoreSummary(
            event_count=total,
            critical_count=by_level.get("critical", 0),
            high_count=by_level.get("high", 0),
            medium_count=by_level.get("medium", 0),
            low_count=by_level.get("low", 0),
        )


def normalize_risk_event(event: dict[str, Any]) -> dict[str, Any]:
    risk_level = str(event["risk_level"])
    event_id = int(event["event_id"])
    channel = str(event["channel"])
    amount = float(event["amount"])
    risk_score = float(event["risk_score"])
    action = str(event["action"])
    review = str(event.get("review") or _case_review(risk_level))
    status = str(event.get("status") or _case_status(risk_level))
    audit = event.get("audit")
    if audit is None:
        audit = [
            f"事件 {event_id} 进入实时评分队列，渠道 {channel}，金额 {amount:.2f}",
            f"模型输出 {risk_score:.4f}，风险等级 {risk_level}，建议动作 {action}",
            f"复核结论：{review}",
        ]
    trace = event.get("trace") or {}
    return {
        "event_id": event_id,
        "timestamp": int(event["timestamp"]),
        "src_node": int(event["src_node"]),
        "dst_node": int(event["dst_node"]),
        "edge_type": int(event["edge_type"]),
        "channel": channel,
        "amount": amount,
        "device_fingerprint": str(event["device_fingerprint"]),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "action": action,
        "focus_node": int(event["focus_node"]),
        "src_node_score": float(event["src_node_score"]),
        "dst_node_score": float(event["dst_node_score"]),
        "is_fraud_edge": int(event.get("is_fraud_edge", -1)),
        "explanation": str(event["explanation"]),
        "emitted_at": int(event["emitted_at"]) if event.get("emitted_at") is not None else None,
        "status": status,
        "review": review,
        "trace_json": json.dumps(trace, ensure_ascii=False),
        "audit_json": json.dumps(audit, ensure_ascii=False),
    }


def row_to_case(row: sqlite3.Row) -> dict[str, Any]:
    trace = json.loads(row["trace_json"] or "{}")
    audit = json.loads(row["audit_json"] or "[]")
    return {
        "caseId": f"CASE-{int(row['event_id']):05d}",
        "eventId": int(row["event_id"]),
        "timestamp": int(row["timestamp"]),
        "riskScore": float(row["risk_score"]),
        "riskLevel": str(row["risk_level"]),
        "action": str(row["action"]),
        "status": str(row["status"]),
        "review": str(row["review"]),
        "focusNode": int(row["focus_node"]),
        "srcNode": int(row["src_node"]),
        "dstNode": int(row["dst_node"]),
        "channel": str(row["channel"]),
        "amount": float(row["amount"]),
        "explanation": str(row["explanation"]),
        "trace": {
            "neighborCount": int(trace.get("neighbor_count", trace.get("neighborCount", 0))),
            "fraudNeighborCount": int(trace.get("fraud_neighbor_count", trace.get("fraudNeighborCount", 0))),
            "normalNeighborCount": int(trace.get("normal_neighbor_count", trace.get("normalNeighborCount", 0))),
            "backgroundNeighborCount": int(trace.get("background_neighbor_count", trace.get("backgroundNeighborCount", 0))),
            "incidentEdgeCount": int(trace.get("incident_edge_count", trace.get("incidentEdgeCount", 0))),
            "dominantEdgeType": int(trace.get("dominant_edge_type", trace.get("dominantEdgeType", row["edge_type"]))),
            "dominantEdgeTypeShare": float(trace.get("dominant_edge_type_share", trace.get("dominantEdgeTypeShare", 0.0))),
            "timeSpan": int(trace.get("time_span", trace.get("timeSpan", 0))),
        },
        "audit": audit,
    }


def events_from_csv_and_trace(risk_path: Path, trace_path: Path | None = None) -> list[dict[str, Any]]:
    frame = pd.read_csv(risk_path)
    traces_by_event: dict[int, dict[str, Any]] = {}
    if trace_path and trace_path.exists():
        trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
        traces_by_event = {int(item["event_id"]): item for item in trace_data.get("traces", [])}
    events: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        event_id = int(row["event_id"])
        if event_id in traces_by_event:
            row["trace"] = traces_by_event[event_id]
        events.append(row)
    return events


def events_from_jsonl(jsonl_path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events
