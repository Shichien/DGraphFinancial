from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .schemas import RiskDecision


class RiskEventRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def upsert_decision(self, decision: RiskDecision) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO risk_events (
                        event_id, event_time, src_account, dst_account,
                        risk_score, risk_level, decision, community_id, evidence_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (event_id) DO UPDATE SET
                        risk_score = EXCLUDED.risk_score,
                        risk_level = EXCLUDED.risk_level,
                        decision = EXCLUDED.decision,
                        community_id = EXCLUDED.community_id,
                        evidence_json = EXCLUDED.evidence_json
                    """,
                    (
                        decision.event_id,
                        decision.timestamp,
                        decision.src_account,
                        decision.dst_account,
                        decision.risk_score,
                        decision.risk_level,
                        decision.decision,
                        decision.community_id,
                        json.dumps(decision.evidence, ensure_ascii=False),
                    ),
                )
                cur.executemany(
                    """
                    INSERT INTO risk_event_reasons (event_id, reason_code)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    [(decision.event_id, reason) for reason in decision.reason_codes],
                )
                cur.executemany(
                    """
                    INSERT INTO risk_event_edges (event_id, src_account, dst_account, relation_type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        (decision.event_id, decision.src_account, node, "related_node")
                        for node in decision.related_nodes
                        if node != decision.src_account
                    ],
                )
                cur.execute(
                    """
                    INSERT INTO risk_audit_logs (event_id, action, detail)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        decision.event_id,
                        "risk_decision_created",
                        f"{decision.risk_level}:{decision.decision}",
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO case_actions (event_id, status, reviewer, note)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        decision.event_id,
                        "pending_review" if decision.risk_level in {"critical", "high"} else "auto_pass",
                        "system",
                        "created by realtime scoring worker",
                    ),
                )

    def dashboard_snapshot(self, limit: int = 80) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT risk_level, COUNT(*) AS count
                    FROM risk_events
                    GROUP BY risk_level
                    """
                )
                level_counts = {str(row["risk_level"]): int(row["count"]) for row in cur.fetchall()}
                cur.execute(
                    """
                    SELECT
                        event_id, event_time, src_account, dst_account,
                        risk_score, risk_level, decision, community_id, evidence_json
                    FROM risk_events
                    ORDER BY event_time DESC, event_id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                events = [dict(row) for row in cur.fetchall()]
                event_ids = [int(row["event_id"]) for row in events]
                reason_map: dict[int, list[str]] = {event_id: [] for event_id in event_ids}
                edge_map: dict[int, list[dict[str, Any]]] = {event_id: [] for event_id in event_ids}
                if event_ids:
                    cur.execute(
                        """
                        SELECT event_id, reason_code
                        FROM risk_event_reasons
                        WHERE event_id = ANY(%s)
                        ORDER BY event_id, reason_code
                        """,
                        (event_ids,),
                    )
                    for row in cur.fetchall():
                        reason_map.setdefault(int(row["event_id"]), []).append(str(row["reason_code"]))
                    cur.execute(
                        """
                        SELECT event_id, src_account, dst_account, relation_type
                        FROM risk_event_edges
                        WHERE event_id = ANY(%s)
                        ORDER BY event_id, src_account, dst_account, relation_type
                        """,
                        (event_ids,),
                    )
                    for row in cur.fetchall():
                        event_id = int(row["event_id"])
                        edge = {
                            "event_id": event_id,
                            "src_account": int(row["src_account"]),
                            "dst_account": int(row["dst_account"]),
                            "relation_type": str(row["relation_type"]),
                        }
                        edge_map.setdefault(event_id, []).append(edge)
                for event in events:
                    event_id = int(event["event_id"])
                    related_nodes = {
                        int(event["src_account"]),
                        int(event["dst_account"]),
                    }
                    for edge in edge_map.get(event_id, []):
                        related_nodes.add(int(edge["src_account"]))
                        related_nodes.add(int(edge["dst_account"]))
                    event["reason_codes"] = reason_map.get(event_id, [])
                    event["related_edges"] = edge_map.get(event_id, [])
                    event["related_nodes"] = sorted(related_nodes)
                cur.execute(
                    """
                    SELECT src_account AS node_id, MAX(risk_score) AS risk_score, COUNT(*) AS event_count
                    FROM risk_events
                    GROUP BY src_account
                    ORDER BY MAX(risk_score) DESC, COUNT(*) DESC
                    LIMIT 20
                    """
                )
                top_nodes = [dict(row) for row in cur.fetchall()]
                cur.execute("SELECT COUNT(*) AS count FROM risk_events")
                total_events = int(cur.fetchone()["count"])
                cur.execute(
                    """
                    SELECT
                        evidence_json ->> 'fraud_script_type' AS fraud_script_type,
                        COUNT(*) AS count,
                        MAX(risk_score) AS max_risk_score,
                        AVG(risk_score) AS avg_risk_score
                    FROM risk_events
                    WHERE COALESCE(evidence_json ->> 'fraud_script_type', 'none') <> 'none'
                    GROUP BY evidence_json ->> 'fraud_script_type'
                    ORDER BY COUNT(*) DESC, MAX(risk_score) DESC
                    LIMIT 12
                    """
                )
                fraud_scripts = [dict(row) for row in cur.fetchall()]
        return {
            "total_events": total_events,
            "risk_level_counts": level_counts,
            "events": events,
            "top_nodes": top_nodes,
            "fraud_scripts": fraud_scripts,
        }

    def node_neighborhood(self, node_id: int, limit: int = 120) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT event_id, src_account, dst_account, relation_type
                    FROM risk_event_edges
                    WHERE src_account = %s OR dst_account = %s
                    ORDER BY event_id DESC
                    LIMIT %s
                    """,
                    (node_id, node_id, limit),
                )
                edges = [dict(row) for row in cur.fetchall()]
                node_ids = {node_id}
                for edge in edges:
                    node_ids.add(int(edge["src_account"]))
                    node_ids.add(int(edge["dst_account"]))
        return {
            "node_id": node_id,
            "nodes": [{"id": item} for item in sorted(node_ids)],
            "edges": edges,
        }

    def audit_logs(self, limit: int = 60) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT audit_id, event_id, action, detail, created_at
                    FROM risk_audit_logs
                    ORDER BY created_at DESC, audit_id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def case_actions(self, limit: int = 60) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT case_id, event_id, status, reviewer, note, updated_at
                    FROM case_actions
                    ORDER BY updated_at DESC, case_id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def record_case_action(self, event_id: int, status: str, reviewer: str, note: str) -> dict[str, Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO case_actions (event_id, status, reviewer, note)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (event_id, status) DO UPDATE SET
                        reviewer = EXCLUDED.reviewer,
                        note = EXCLUDED.note,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING case_id, event_id, status, reviewer, note, updated_at
                    """,
                    (event_id, status, reviewer, note),
                )
                action = dict(cur.fetchone())
                cur.execute(
                    """
                    INSERT INTO risk_audit_logs (event_id, action, detail)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        event_id,
                        "case_action_recorded",
                        f"{status}:{reviewer}:{note}",
                    ),
                )
                return action
