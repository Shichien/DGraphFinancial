from __future__ import annotations

import time
from typing import Any

import psycopg
import requests
from confluent_kafka import Consumer, Producer
from neo4j import GraphDatabase
from psycopg.rows import dict_row
from redis import Redis

from .kafka_runtime import produce_simulated_transactions


TOPICS = [
    "transactions.raw",
    "accounts.raw",
    "devices.raw",
    "blacklist.raw",
    "labels.delayed",
    "transactions.cleaned",
    "features.realtime",
    "risk.scored",
    "risk.alerts",
    "risk.audit",
]


def run_e2e_check(
    *,
    event_count: int,
    interval_ms: int,
    seed: int,
    timeout_sec: int,
    bootstrap_servers: str,
    database_url: str,
    redis_url: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    api_url: str,
) -> dict[str, Any]:
    run_id = int(time.time() * 1000)
    event_id_start = run_id
    timestamp_start = run_id
    _check_kafka(bootstrap_servers)
    _check_database(database_url)
    _check_redis(redis_url)
    _check_neo4j(neo4j_uri, neo4j_user, neo4j_password)
    _check_api(api_url)
    time.sleep(3)

    produce_simulated_transactions(
        bootstrap_servers=bootstrap_servers,
        topic="transactions.raw",
        event_count=event_count,
        interval_ms=interval_ms,
        seed=seed,
        event_id_start=event_id_start,
        timestamp_start=timestamp_start,
    )
    expected_scored_floor = max(1, int(event_count * 0.85))
    expected_redis_floor = min(expected_scored_floor, 200)
    deadline = time.monotonic() + timeout_sec
    last_state: dict[str, Any] = {}
    while time.monotonic() < deadline:
        postgres_state = _postgres_state(database_url, event_id_start, event_count)
        redis_state = _redis_state(redis_url, event_id_start, event_count)
        neo4j_state = _neo4j_state(neo4j_uri, neo4j_user, neo4j_password, event_id_start)
        dashboard_state = _dashboard_state(api_url)
        last_state = {
            "postgres": postgres_state,
            "redis": redis_state,
            "neo4j": neo4j_state,
            "dashboard": dashboard_state,
        }
        if (
            postgres_state["risk_events"] >= expected_scored_floor
            and postgres_state["audit_rows"] >= expected_scored_floor
            and postgres_state["case_rows"] >= expected_scored_floor
            and postgres_state["reason_rows"] > 0
            and postgres_state["edge_rows"] > 0
            and postgres_state["alert_rows"] > 0
            and postgres_state["script_rows"] > 0
            and postgres_state["script_reason_rows"] > 0
            and redis_state["run_risk_events"] >= expected_redis_floor
            and neo4j_state["transfer_edges"] >= expected_scored_floor
            and dashboard_state["total_events"] >= postgres_state["risk_events"]
            and dashboard_state["visible_nodes"] > 0
            and dashboard_state["visible_edges"] > 0
            and dashboard_state["recent_events"] > 0
            and dashboard_state["alert_count"] > 0
            and dashboard_state["fraud_script_count"] > 0
        ):
            return {
                "ok": True,
                "run_id": run_id,
                "event_count": event_count,
                "expected_scored_floor": expected_scored_floor,
                "expected_redis_floor": expected_redis_floor,
                **last_state,
            }
        time.sleep(2)
    return {
        "ok": False,
        "run_id": run_id,
        "event_count": event_count,
        "expected_scored_floor": expected_scored_floor,
        "expected_redis_floor": expected_redis_floor,
        "last_state": last_state,
        "message": "端到端验收超时。请确认 feature-worker、scoring-worker、API 和基础设施均已启动。",
    }


def _check_kafka(bootstrap_servers: str) -> None:
    producer = Producer({"bootstrap.servers": bootstrap_servers, "socket.timeout.ms": 5000})
    metadata = producer.list_topics(timeout=8)
    missing = [topic for topic in TOPICS if topic not in metadata.topics]
    if missing:
        raise RuntimeError("Kafka 缺少主题：" + ", ".join(missing))
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"dgcheater-e2e-check-{int(time.time() * 1000)}",
            "enable.auto.commit": False,
            "auto.offset.reset": "latest",
        }
    )
    consumer.close()


def _check_database(database_url: str) -> None:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()


def _check_redis(redis_url: str) -> None:
    client = Redis.from_url(redis_url, decode_responses=True)
    client.ping()


def _check_neo4j(uri: str, user: str, password: str) -> None:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            session.run("RETURN 1").single()
    finally:
        driver.close()


def _check_api(api_url: str) -> None:
    response = requests.get(api_url.rstrip("/") + "/health", timeout=8)
    response.raise_for_status()


def _postgres_state(database_url: str, event_id_start: int, event_count: int) -> dict[str, int]:
    event_id_end = event_id_start + event_count
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_events
                WHERE event_id >= %s AND event_id < %s
                """,
                (event_id_start, event_id_end),
            )
            risk_events = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_event_reasons
                WHERE event_id >= %s AND event_id < %s
                """,
                (event_id_start, event_id_end),
            )
            reason_rows = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_event_edges
                WHERE event_id >= %s AND event_id < %s
                """,
                (event_id_start, event_id_end),
            )
            edge_rows = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_audit_logs
                WHERE event_id >= %s AND event_id < %s
                """,
                (event_id_start, event_id_end),
            )
            audit_rows = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM case_actions
                WHERE event_id >= %s AND event_id < %s
                """,
                (event_id_start, event_id_end),
            )
            case_rows = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_events
                WHERE event_id >= %s AND event_id < %s
                  AND risk_level IN ('critical', 'high')
                """,
                (event_id_start, event_id_end),
            )
            alert_rows = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_events
                WHERE event_id >= %s AND event_id < %s
                  AND COALESCE(evidence_json ->> 'fraud_script_type', 'none') <> 'none'
                """,
                (event_id_start, event_id_end),
            )
            script_rows = int(cur.fetchone()["count"])
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM risk_event_reasons
                WHERE event_id >= %s AND event_id < %s
                  AND reason_code = 'script-pattern:matched'
                """,
                (event_id_start, event_id_end),
            )
            script_reason_rows = int(cur.fetchone()["count"])
    return {
        "risk_events": risk_events,
        "reason_rows": reason_rows,
        "edge_rows": edge_rows,
        "audit_rows": audit_rows,
        "case_rows": case_rows,
        "alert_rows": alert_rows,
        "script_rows": script_rows,
        "script_reason_rows": script_reason_rows,
    }


def _redis_state(redis_url: str, event_id_start: int = 0, event_count: int = 0) -> dict[str, int]:
    client = Redis.from_url(redis_url, decode_responses=True)
    event_id_end = event_id_start + event_count
    run_risk_events = 0
    for item in client.lrange("recent_alerts", 0, 199):
        try:
            event_id = int(__import__("json").loads(item).get("event_id", -1))
        except (TypeError, ValueError):
            continue
        if event_id_start <= event_id < event_id_end:
            run_risk_events += 1
    return {
        "top_risk_nodes": int(client.zcard("top_risk_nodes")),
        "recent_alerts": int(client.llen("recent_alerts")),
        "run_risk_events": run_risk_events,
        "community_risk_rank": int(client.zcard("community_risk_rank")),
    }


def _neo4j_state(uri: str, user: str, password: str, event_id_start: int) -> dict[str, int]:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            transfer_edges = session.run(
                """
                MATCH (:Account)-[r:TRANSFERRED_TO]->(:Account)
                WHERE r.event_id >= $event_id_start
                RETURN count(r) AS count
                """,
                event_id_start=event_id_start,
            ).single()
            account_nodes = session.run(
                """
                MATCH (a:Account)
                WHERE a.updated_at IS NOT NULL
                RETURN count(a) AS count
                """
            ).single()
    finally:
        driver.close()
    return {
        "transfer_edges": int(transfer_edges["count"]) if transfer_edges else 0,
        "account_nodes": int(account_nodes["count"]) if account_nodes else 0,
    }


def _dashboard_state(api_url: str) -> dict[str, int]:
    response = requests.get(api_url.rstrip("/") + "/api/graph-stream", timeout=8)
    response.raise_for_status()
    payload = response.json()
    summary = payload.get("summary", {})
    return {
        "total_events": int(summary.get("total", 0)),
        "visible_nodes": int(summary.get("visibleNodeCount", 0)),
        "visible_edges": int(summary.get("visibleEdgeCount", 0)),
        "recent_events": len(payload.get("recentEvents", [])),
        "alert_count": int(summary.get("alertCount", 0)),
        "fraud_script_count": len(payload.get("fraudScripts", [])),
    }
