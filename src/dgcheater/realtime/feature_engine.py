from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .graph_state import InMemoryGraphState
from .schemas import AccountProfileEvent, BlacklistEvent, DeviceLoginEvent, RealtimeFeatures, TransactionEvent


@dataclass(slots=True)
class AccountState:
    events: deque[TransactionEvent]
    counterparties: set[int]
    channels: deque[str]
    login_results: deque[tuple[int, str]]
    historical_risk_score: float = 0.0
    account_age_days: int = 0
    last_timestamp: int | None = None


class RealtimeFeatureEngine:
    def __init__(self, graph: InMemoryGraphState | None = None) -> None:
        self.graph = graph or InMemoryGraphState()
        self.accounts: dict[int, AccountState] = defaultdict(
            lambda: AccountState(deque(maxlen=2_000), set(), deque(maxlen=40), deque(maxlen=200))
        )
        self.device_accounts: dict[str, set[int]] = defaultdict(set)
        self.ip_accounts: dict[str, set[int]] = defaultdict(set)
        self.merchant_amounts: dict[str, deque[tuple[int, float]]] = defaultdict(lambda: deque(maxlen=2_000))
        self.in_degree: dict[int, int] = defaultdict(int)
        self.out_degree: dict[int, int] = defaultdict(int)
        self.blacklisted_accounts: set[int] = set()
        self.blacklisted_devices: set[str] = set()
        self.blacklisted_ips: set[str] = set()
        self.blacklisted_merchants: set[str] = set()

    def ingest_account(self, event: AccountProfileEvent) -> None:
        state = self.accounts[event.account_id]
        state.historical_risk_score = event.historical_risk_score
        state.account_age_days = event.account_age_days

    def ingest_device(self, event: DeviceLoginEvent) -> None:
        state = self.accounts[event.account_id]
        state.login_results.append((event.timestamp, event.login_result))
        self.device_accounts[event.device_id].add(event.account_id)
        self.ip_accounts[event.ip].add(event.account_id)

    def ingest_blacklist(self, event: BlacklistEvent) -> None:
        if event.entity_type == "account":
            self.blacklisted_accounts.add(int(event.entity_id))
        elif event.entity_type == "device":
            self.blacklisted_devices.add(event.entity_id)
        elif event.entity_type == "ip":
            self.blacklisted_ips.add(event.entity_id)
        elif event.entity_type == "merchant":
            self.blacklisted_merchants.add(event.entity_id)

    def transform(self, event: TransactionEvent) -> RealtimeFeatures:
        src_state = self.accounts[event.src_account]
        seconds_since_last = 0 if src_state.last_timestamp is None else max(event.timestamp - src_state.last_timestamp, 0)
        self.graph.ingest(event)
        self._update_state(event)

        src_state = self.accounts[event.src_account]
        src_1m_events = [item for item in src_state.events if event.timestamp - item.timestamp <= 60]
        src_5m_amount = sum(item.amount for item in src_state.events if event.timestamp - item.timestamp <= 300)
        src_10m_counterparties = {
            item.dst_account
            for item in src_state.events
            if event.timestamp - item.timestamp <= 600
        }
        channel_switch_count = sum(
            1
            for prev, cur in zip(src_state.channels, list(src_state.channels)[1:])
            if prev != cur
        )
        merchant_window = self.merchant_amounts[event.merchant_id]
        merchant_in_amount = sum(amount for ts, amount in merchant_window if event.timestamp - ts <= 300)
        graph_features = self.graph.features(event.src_account)
        recent_login_challenge_count = sum(
            1
            for timestamp, result in src_state.login_results
            if result == "challenge" and event.timestamp - timestamp <= 600
        )
        blacklist_hit_count = int(event.src_account in self.blacklisted_accounts) + int(event.dst_account in self.blacklisted_accounts)
        blacklist_hit_count += int(event.device_id in self.blacklisted_devices)
        blacklist_hit_count += int(event.ip in self.blacklisted_ips)
        blacklist_hit_count += int(event.merchant_id in self.blacklisted_merchants)

        burst_score = min(len(src_1m_events) / 12.0 + event.amount / 150_000.0, 1.0)
        script_score = self._script_pattern_score(
            amount=event.amount,
            src_1m_count=len(src_1m_events),
            src_5m_amount=src_5m_amount,
            counterparty_count=len(src_10m_counterparties),
            device_account_count=len(self.device_accounts[event.device_id]),
            ip_account_count=len(self.ip_accounts[event.ip]),
            merchant_in_amount=merchant_in_amount,
            channel_switch_count=channel_switch_count,
            graph_neighbor_count=graph_features.neighbor_count,
            graph_component_size=graph_features.component_size,
        )
        return RealtimeFeatures(
            event_id=event.event_id,
            timestamp=event.timestamp,
            src_account=event.src_account,
            dst_account=event.dst_account,
            amount=event.amount,
            source_channel=event.source_channel,
            device_id=event.device_id,
            ip=event.ip,
            merchant_id=event.merchant_id,
            edge_type=event.edge_type,
            scenario_id=event.scenario_id,
            fraud_script_type=event.fraud_script_type,
            is_scripted_fraud=event.is_scripted_fraud,
            src_1m_count=len(src_1m_events),
            src_5m_amount=round(src_5m_amount, 2),
            src_10m_counterparty_count=len(src_10m_counterparties),
            device_account_count=len(self.device_accounts[event.device_id]),
            ip_account_count=len(self.ip_accounts[event.ip]),
            merchant_in_amount=round(merchant_in_amount, 2),
            src_out_degree=self.out_degree[event.src_account],
            dst_in_degree=self.in_degree[event.dst_account],
            seconds_since_last_src_event=seconds_since_last,
            channel_switch_count=channel_switch_count,
            burst_score=burst_score,
            graph_neighbor_count=graph_features.neighbor_count,
            graph_risky_neighbor_count=graph_features.risky_neighbor_count,
            graph_component_size=graph_features.component_size,
            graph_community_id=graph_features.community_id,
            graph_related_nodes=graph_features.related_nodes,
            historical_risk_score=round(src_state.historical_risk_score, 4),
            account_age_days=src_state.account_age_days,
            recent_login_challenge_count=recent_login_challenge_count,
            blacklist_hit_count=blacklist_hit_count,
            script_score=script_score,
        )

    def _update_state(self, event: TransactionEvent) -> None:
        src_state = self.accounts[event.src_account]
        src_state.events.append(event)
        src_state.counterparties.add(event.dst_account)
        src_state.channels.append(event.source_channel)
        src_state.last_timestamp = event.timestamp
        self.device_accounts[event.device_id].update({event.src_account, event.dst_account})
        self.ip_accounts[event.ip].update({event.src_account, event.dst_account})
        self.merchant_amounts[event.merchant_id].append((event.timestamp, event.amount))
        self.out_degree[event.src_account] += 1
        self.in_degree[event.dst_account] += 1

    @staticmethod
    def _script_pattern_score(
        *,
        amount: float,
        src_1m_count: int,
        src_5m_amount: float,
        counterparty_count: int,
        device_account_count: int,
        ip_account_count: int,
        merchant_in_amount: float,
        channel_switch_count: int,
        graph_neighbor_count: int,
        graph_component_size: int,
    ) -> float:
        shared_identity = min(device_account_count / 4.0, 1.0) * 0.30 + min(ip_account_count / 6.0, 1.0) * 0.25
        burst_transfer = min(src_1m_count / 6.0, 1.0) * 0.20 + min(src_5m_amount / 150_000.0, 1.0) * 0.25
        large_amount = min(amount / 90_000.0, 1.0) * 0.18
        graph_cluster = min(graph_neighbor_count / 8.0, 1.0) * 0.18 + min(graph_component_size / 32.0, 1.0) * 0.12
        merchant_concentration = min(merchant_in_amount / 180_000.0, 1.0) * 0.16
        channel_evasion = min(channel_switch_count / 6.0, 1.0) * 0.12
        return min(
            shared_identity
            + burst_transfer
            + large_amount
            + graph_cluster
            + merchant_concentration
            + channel_evasion,
            1.0,
        )
