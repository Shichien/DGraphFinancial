from __future__ import annotations

import json
import time
from typing import Any

from neo4j import GraphDatabase
from redis import Redis

from .schemas import RealtimeFeatures, RiskDecision


class RedisRiskSink:
    def __init__(self, redis_url: str) -> None:
        self.client = Redis.from_url(redis_url, decode_responses=True)

    def write(self, decision: RiskDecision) -> None:
        payload = json.dumps(decision.to_dict(), ensure_ascii=False, separators=(",", ":"))
        community = decision.community_id or f"comm-{decision.src_account}"
        pipe = self.client.pipeline()
        pipe.zadd("top_risk_nodes", {str(decision.src_account): decision.risk_score})
        pipe.zadd("community_risk_rank", {community: decision.risk_score})
        pipe.lpush("recent_alerts", payload)
        pipe.ltrim("recent_alerts", 0, 199)
        pipe.hset(f"risk_event:{decision.event_id}", mapping=_flat_mapping(decision.to_dict()))
        pipe.expire(f"risk_event:{decision.event_id}", 86_400)
        pipe.execute()

    def snapshot(self, limit: int = 20) -> dict[str, Any]:
        top_nodes = self.client.zrevrange("top_risk_nodes", 0, limit - 1, withscores=True)
        communities = self.client.zrevrange("community_risk_rank", 0, limit - 1, withscores=True)
        alerts = [json.loads(item) for item in self.client.lrange("recent_alerts", 0, limit - 1)]
        return {
            "top_risk_nodes": [{"node_id": int(node), "risk_score": float(score)} for node, score in top_nodes],
            "community_risk_rank": [{"community_id": community, "risk_score": float(score)} for community, score in communities],
            "recent_alerts": alerts,
        }


class Neo4jGraphSink:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def write(self, features: RealtimeFeatures, decision: RiskDecision) -> None:
        with self.driver.session() as session:
            session.execute_write(_merge_graph_event, features.to_dict(), decision.to_dict(), int(time.time()))


class RealtimeSinkBundle:
    def __init__(self, redis_sink: RedisRiskSink | None = None, graph_sink: Neo4jGraphSink | None = None) -> None:
        self.redis_sink = redis_sink
        self.graph_sink = graph_sink

    def write(self, features: RealtimeFeatures, decision: RiskDecision) -> None:
        if self.redis_sink is not None:
            self.redis_sink.write(decision)
        if self.graph_sink is not None:
            self.graph_sink.write(features, decision)

    def close(self) -> None:
        if self.graph_sink is not None:
            self.graph_sink.close()


def _merge_graph_event(tx: Any, features: dict[str, Any], decision: dict[str, Any], observed_at: int) -> None:
    tx.run(
        """
        MERGE (src:Account {id: $src_account})
        MERGE (dst:Account {id: $dst_account})
        MERGE (device:Device {id: $device_id})
        MERGE (ip:IP {id: $ip})
        MERGE (merchant:Merchant {id: $merchant_id})
        MERGE (src)-[txrel:TRANSFERRED_TO {event_id: $event_id}]->(dst)
        SET txrel.amount = $amount,
            txrel.timestamp = $timestamp,
            txrel.channel = $source_channel,
            txrel.edge_type = $edge_type,
            txrel.risk_score = $risk_score,
            txrel.risk_level = $risk_level,
            txrel.decision = $decision,
            txrel.observed_at = $observed_at
        MERGE (src)-[:USED_DEVICE]->(device)
        MERGE (src)-[:USED_IP]->(ip)
        MERGE (src)-[:PAID_MERCHANT]->(merchant)
        SET src.last_risk_score = $risk_score,
            src.last_risk_level = $risk_level,
            src.community_id = $community_id,
            src.updated_at = $observed_at
        """,
        {
            **features,
            "risk_score": decision["risk_score"],
            "risk_level": decision["risk_level"],
            "decision": decision["decision"],
            "community_id": decision["community_id"],
            "observed_at": observed_at,
        },
    )


def _flat_mapping(payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            result[key] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            result[key] = str(value)
    return result
