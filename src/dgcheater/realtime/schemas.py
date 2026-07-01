from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RiskLevel = Literal["critical", "high", "medium", "low"]


@dataclass(slots=True)
class TransactionEvent:
    event_id: int
    timestamp: int
    source_channel: str
    src_account: int
    dst_account: int
    amount: float
    merchant_id: str
    device_id: str
    ip: str
    geo: str
    edge_type: int
    scenario_id: str
    is_scripted_fraud: bool
    fraud_script_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AccountProfileEvent:
    event_id: int
    timestamp: int
    account_id: int
    account_age_days: int
    historical_risk_score: float
    home_geo: str
    segment: str
    scenario_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DeviceLoginEvent:
    event_id: int
    timestamp: int
    account_id: int
    device_id: str
    ip: str
    geo: str
    source_channel: str
    login_result: str
    scenario_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BlacklistEvent:
    event_id: int
    timestamp: int
    account_id: int
    entity_type: str
    entity_id: str
    risk_reason: str
    expires_at: int
    scenario_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DelayedLabelEvent:
    event_id: int
    timestamp: int
    labeled_event_id: int
    label: str
    label_delay_seconds: int
    fraud_script_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RealtimeFeatures:
    event_id: int
    timestamp: int
    src_account: int
    dst_account: int
    amount: float
    source_channel: str
    device_id: str
    ip: str
    merchant_id: str
    edge_type: int
    scenario_id: str
    fraud_script_type: str
    is_scripted_fraud: bool
    src_1m_count: int
    src_5m_amount: float
    src_10m_counterparty_count: int
    device_account_count: int
    ip_account_count: int
    merchant_in_amount: float
    src_out_degree: int
    dst_in_degree: int
    seconds_since_last_src_event: int
    channel_switch_count: int
    burst_score: float
    graph_neighbor_count: int
    graph_risky_neighbor_count: int
    graph_component_size: int
    graph_community_id: str
    graph_related_nodes: list[int]
    historical_risk_score: float
    account_age_days: int
    recent_login_challenge_count: int
    blacklist_hit_count: int
    script_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RiskDecision:
    event_id: int
    timestamp: int
    src_account: int
    dst_account: int
    risk_score: float
    risk_level: RiskLevel
    decision: str
    reason_codes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    community_id: str = ""
    related_nodes: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
