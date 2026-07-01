from __future__ import annotations

import os
from pathlib import Path

from .dgraph_prior import DGraphAccountPrior
from .schemas import RealtimeFeatures, RiskDecision, RiskLevel

SCORE_WEIGHTS = {
    "offline_model_score": 0.45,
    "realtime_behavior_score": 0.30,
    "graph_community_score": 0.15,
    "rule_score": 0.10,
}


def _clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def risk_level(score: float) -> RiskLevel:
    if score >= 0.78:
        return "critical"
    if score >= 0.50:
        return "high"
    if score >= 0.30:
        return "medium"
    return "low"


class FusionRiskScorer:
    def __init__(self, account_prior: DGraphAccountPrior | None = None, model_dir: Path | None = None) -> None:
        del model_dir
        self.account_prior = account_prior or DGraphAccountPrior.load()

    def score(self, features: RealtimeFeatures) -> RiskDecision:
        rule_score = self._rule_score(features)
        realtime_score = self._realtime_behavior_score(features)
        graph_score = self._graph_score(features)
        offline_score, dgraph_evidence = self._offline_prior_score(features)
        final_score = _clamp01(
            SCORE_WEIGHTS["offline_model_score"] * offline_score
            + SCORE_WEIGHTS["realtime_behavior_score"] * realtime_score
            + SCORE_WEIGHTS["graph_community_score"] * graph_score
            + SCORE_WEIGHTS["rule_score"] * rule_score
        )
        level = risk_level(final_score)
        return RiskDecision(
            event_id=features.event_id,
            timestamp=features.timestamp,
            src_account=features.src_account,
            dst_account=features.dst_account,
            risk_score=final_score,
            risk_level=level,
            decision=self._decision(level),
            reason_codes=self._reason_codes(features, rule_score, realtime_score, graph_score),
            evidence={
                "offline_model_score": offline_score,
                "offline_model_name": self.account_prior.metadata.model_name,
                **dgraph_evidence,
                "realtime_behavior_score": realtime_score,
                "graph_community_score": graph_score,
                "rule_score": rule_score,
                "script_score": features.script_score,
                "fraud_script_type": features.fraud_script_type,
                "scenario_id": features.scenario_id,
                "is_scripted_fraud": features.is_scripted_fraud,
                "source_channel": features.source_channel,
                "amount": features.amount,
                "device_account_count": features.device_account_count,
                "ip_account_count": features.ip_account_count,
                "graph_neighbor_count": features.graph_neighbor_count,
                "graph_community_id": features.graph_community_id,
                "graph_related_node_count": len(features.graph_related_nodes),
                "historical_risk_score": features.historical_risk_score,
                "account_age_days": features.account_age_days,
                "recent_login_challenge_count": features.recent_login_challenge_count,
                "blacklist_hit_count": features.blacklist_hit_count,
            },
            community_id=features.graph_community_id,
            related_nodes=_dedupe_nodes([features.src_account, features.dst_account, *features.graph_related_nodes], limit=80),
        )

    def _rule_score(self, features: RealtimeFeatures) -> float:
        score = 0.0
        if features.amount >= 50_000:
            score += 0.30
        if features.src_1m_count >= 6:
            score += 0.20
        if features.device_account_count >= 4:
            score += 0.18
        if features.ip_account_count >= 6:
            score += 0.16
        if features.channel_switch_count >= 3:
            score += 0.10
        if features.recent_login_challenge_count >= 2:
            score += 0.12
        if features.blacklist_hit_count > 0:
            score += 0.34
        if features.script_score >= 0.65:
            score += 0.26
        return _clamp01(score)

    def _realtime_behavior_score(self, features: RealtimeFeatures) -> float:
        return _clamp01(
            features.burst_score * 0.22
            + min(features.src_5m_amount / 200_000.0, 1.0) * 0.16
            + min(features.src_10m_counterparty_count / 20.0, 1.0) * 0.15
            + min(features.channel_switch_count / 8.0, 1.0) * 0.12
            + min(features.recent_login_challenge_count / 4.0, 1.0) * 0.10
            + min(features.blacklist_hit_count, 1) * 0.12
            + min(features.device_account_count / 4.0, 1.0) * 0.08
            + min(features.ip_account_count / 6.0, 1.0) * 0.07
            + features.script_score * 0.08
        )

    def _graph_score(self, features: RealtimeFeatures) -> float:
        return _clamp01(
            min(features.graph_neighbor_count / 36.0, 1.0) * 0.35
            + min(features.graph_risky_neighbor_count / 8.0, 1.0) * 0.45
            + min(features.graph_component_size / 120.0, 1.0) * 0.20
        )

    def _offline_prior_score(self, features: RealtimeFeatures) -> tuple[float, dict[str, float | int | str]]:
        src_score, src_dgraph_node = self.account_prior.score_account(features.src_account)
        dst_score, dst_dgraph_node = self.account_prior.score_account(features.dst_account)
        score = max(src_score, dst_score)
        return _clamp01(score), {
            "dgraph_src_account_score": _clamp01(src_score),
            "dgraph_dst_account_score": _clamp01(dst_score),
            "dgraph_src_node_id": src_dgraph_node,
            "dgraph_dst_node_id": dst_dgraph_node,
            "dgraph_prior_feature_count": self.account_prior.metadata.feature_count,
            "dgraph_prior_valid_auc": self.account_prior.metadata.valid_auc,
        }

    @staticmethod
    def _decision(level: RiskLevel) -> str:
        return {
            "critical": "freeze_and_manual_review",
            "high": "manual_review",
            "medium": "step_up_verification",
            "low": "pass",
        }[level]

    @staticmethod
    def _reason_codes(features: RealtimeFeatures, rule_score: float, realtime_score: float, graph_score: float) -> list[str]:
        reasons: list[str] = []
        if features.script_score >= 0.65:
            reasons.append("script-pattern:matched")
        if features.amount >= 50_000:
            reasons.append("amount:large")
        if features.device_account_count >= 4:
            reasons.append("device:shared")
        if features.ip_account_count >= 6:
            reasons.append("ip:cluster")
        if features.recent_login_challenge_count >= 2:
            reasons.append("device-login:challenge")
        if features.blacklist_hit_count > 0:
            reasons.append("blacklist:hit")
        if features.historical_risk_score >= 0.55:
            reasons.append("account:historical-risk")
        if max(features.src_account, features.dst_account) >= 0:
            reasons.append("model:dgraph-prior")
        if graph_score >= 0.45:
            reasons.append("graph:community-risk")
        if realtime_score >= 0.45:
            reasons.append("behavior:burst")
        if rule_score >= 0.55:
            reasons.append("rule:multi-hit")
        return reasons or ["model:low-risk"]


def _dedupe_nodes(nodes: list[int], *, limit: int) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for node in nodes:
        if node in seen:
            continue
        seen.add(node)
        result.append(node)
        if len(result) >= limit:
            break
    return result
