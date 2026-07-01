from __future__ import annotations

from dataclasses import dataclass
import itertools
import random
from typing import Iterable, NamedTuple

from .schemas import AccountProfileEvent, BlacklistEvent, DelayedLabelEvent, DeviceLoginEvent, TransactionEvent


CHANNELS = ("bank_transfer", "wallet_pay", "merchant_acquire", "qr_pay", "mobile_banking")
GEOS = ("CN-SH", "CN-BJ", "CN-GD", "CN-ZJ", "CN-SC", "CN-HK")
FRAUD_TYPES = (
    "fan_in_cashout",
    "probe_then_drain",
    "cycle_transfer",
    "device_reuse",
    "ip_cluster",
    "merchant_laundering",
    "cross_channel_evasion",
    "burst_transfer",
)
SEGMENTS = ("retail", "small_business", "merchant_operator", "cross_border", "new_account")
ACTIVE_FRAUD_GROUP_COUNT = 12


class MultiSourceEventBatch(NamedTuple):
    transaction: TransactionEvent
    account: AccountProfileEvent
    device: DeviceLoginEvent
    blacklist: BlacklistEvent | None
    delayed_label: DelayedLabelEvent | None


@dataclass(slots=True)
class SimulatorConfig:
    account_count: int = 12_000
    merchant_count: int = 420
    device_count: int = 6_000
    fraud_ratio: float = 0.26
    seed: int = 42
    event_id_start: int = 0
    timestamp_start: int = 0


class MultiSourceFraudSimulator:
    def __init__(self, config: SimulatorConfig | None = None) -> None:
        self.config = config or SimulatorConfig()
        self.rng = random.Random(self.config.seed)
        self.event_counter = itertools.count(self.config.event_id_start)
        self.fraud_groups = self._build_fraud_groups()
        self.group_assets = self._build_group_assets()

    def stream(self, event_count: int) -> Iterable[TransactionEvent]:
        for offset in range(event_count):
            timestamp = self.config.timestamp_start + offset
            if self.rng.random() < self.config.fraud_ratio:
                yield self._scripted_event(timestamp)
            else:
                yield self._normal_event(timestamp)

    def multi_source_stream(self, event_count: int) -> Iterable[MultiSourceEventBatch]:
        for transaction in self.stream(event_count):
            yield MultiSourceEventBatch(
                transaction=transaction,
                account=self._account_event(transaction),
                device=self._device_event(transaction),
                blacklist=self._blacklist_event(transaction),
                delayed_label=self._delayed_label_event(transaction),
            )

    def _normal_event(self, timestamp: int) -> TransactionEvent:
        src = self.rng.randrange(self.config.account_count)
        dst = self.rng.randrange(self.config.account_count)
        while dst == src:
            dst = self.rng.randrange(self.config.account_count)
        channel = self.rng.choice(CHANNELS)
        amount = round(min(self.rng.lognormvariate(3.05, 0.82), 60_000), 2)
        return self._event(
            timestamp=timestamp,
            src=src,
            dst=dst,
            channel=channel,
            amount=amount,
            scenario_id="normal",
            fraud_type="none",
            scripted=False,
        )

    def _scripted_event(self, timestamp: int) -> TransactionEvent:
        fraud_type = self.rng.choice(FRAUD_TYPES)
        active_group_count = min(len(self.fraud_groups), ACTIVE_FRAUD_GROUP_COUNT)
        group_index = self.rng.randrange(active_group_count)
        group = self.fraud_groups[group_index]
        hub = group[0]
        members = group[1:]
        if fraud_type == "fan_in_cashout":
            src = self.rng.choice(members)
            dst = hub
            amount = self.rng.uniform(800, 9_000)
        elif fraud_type == "probe_then_drain":
            src = hub
            dst = self.rng.choice(members)
            amount = self.rng.choice([12.8, 18.6, 25.0, self.rng.uniform(18_000, 90_000)])
        elif fraud_type == "cycle_transfer":
            src = self.rng.choice(group)
            dst = group[(group.index(src) + 1) % len(group)]
            amount = self.rng.uniform(1_200, 25_000)
        elif fraud_type == "device_reuse":
            src = self.rng.choice(members)
            dst = self.rng.choice(group)
            amount = self.rng.uniform(600, 18_000)
        elif fraud_type == "ip_cluster":
            src = self.rng.choice(members)
            dst = hub
            amount = self.rng.uniform(400, 16_000)
        elif fraud_type == "merchant_laundering":
            src = self.rng.choice(group)
            dst = hub
            amount = self.rng.uniform(2_000, 70_000)
        elif fraud_type == "cross_channel_evasion":
            src = hub
            dst = self.rng.choice(members)
            amount = self.rng.uniform(500, 22_000)
        else:
            src = self.rng.choice(group)
            dst = self.rng.choice(members)
            amount = self.rng.uniform(8_000, 120_000)
        return self._event(
            timestamp=timestamp,
            src=src,
            dst=dst,
            channel=self.rng.choice(CHANNELS),
            amount=round(amount, 2),
            scenario_id=f"script-{group_index:03d}-{fraud_type}",
            fraud_type=fraud_type,
            scripted=True,
            group_index=group_index,
        )

    def _event(
        self,
        timestamp: int,
        src: int,
        dst: int,
        channel: str,
        amount: float,
        scenario_id: str,
        fraud_type: str,
        scripted: bool,
        group_index: int | None = None,
    ) -> TransactionEvent:
        event_id = next(self.event_counter)
        shared_device = fraud_type in {"device_reuse", "cross_channel_evasion"}
        shared_ip = fraud_type in {"ip_cluster", "burst_transfer"}
        shared_merchant = fraud_type in {"merchant_laundering", "fan_in_cashout"}
        assets = self.group_assets[group_index] if group_index is not None else None
        return TransactionEvent(
            event_id=event_id,
            timestamp=timestamp,
            source_channel=channel,
            src_account=src,
            dst_account=dst,
            amount=amount,
            merchant_id=self._merchant_id(src, scripted, shared_merchant, assets),
            device_id=self._device_id(src, shared_device, assets),
            ip=self._ip(src, shared_ip, assets),
            geo=self.rng.choice(GEOS),
            edge_type=1 + self.rng.randrange(11),
            scenario_id=scenario_id,
            is_scripted_fraud=scripted,
            fraud_script_type=fraud_type,
        )

    def _build_fraud_groups(self) -> list[list[int]]:
        groups: list[list[int]] = []
        for base in range(500, 1_400, 15):
            groups.append([base + offset for offset in range(9)])
        return groups

    def _build_group_assets(self) -> list[dict[str, str]]:
        assets: list[dict[str, str]] = []
        for index, group in enumerate(self.fraud_groups):
            hub = group[0]
            assets.append(
                {
                    "device": f"d_fraud_{index:04d}",
                    "ip": f"172.31.{index % 255}.{(hub % 220) + 20}",
                    "merchant": f"m_fraud_{index:04d}",
                }
            )
        return assets

    def _device_id(self, src: int, shared_device: bool, assets: dict[str, str] | None) -> str:
        if shared_device and assets is not None:
            return assets["device"]
        return f"d_{self.rng.randrange(self.config.device_count):06d}"

    def _ip(self, src: int, shared_ip: bool, assets: dict[str, str] | None) -> str:
        if shared_ip and assets is not None:
            return assets["ip"]
        return f"10.{(src // 256) % 255}.{src % 255}.{self.rng.randrange(1, 255)}"

    def _merchant_id(self, src: int, scripted: bool, shared_merchant: bool, assets: dict[str, str] | None) -> str:
        if shared_merchant and assets is not None:
            return assets["merchant"]
        upper_bound = self.config.merchant_count if not scripted else max(12, self.config.merchant_count // 8)
        return f"m_{self.rng.randrange(upper_bound):05d}"

    def _account_event(self, event: TransactionEvent) -> AccountProfileEvent:
        account_age_days = 3 + ((event.src_account * 37) % 2400)
        historical_risk = min(0.92, 0.12 + (event.src_account % 97) / 180.0)
        if event.is_scripted_fraud:
            historical_risk = min(0.98, historical_risk + 0.22)
        return AccountProfileEvent(
            event_id=event.event_id,
            timestamp=event.timestamp,
            account_id=event.src_account,
            account_age_days=account_age_days,
            historical_risk_score=round(historical_risk, 4),
            home_geo=event.geo,
            segment=self.rng.choice(SEGMENTS),
            scenario_id=event.scenario_id,
        )

    def _device_event(self, event: TransactionEvent) -> DeviceLoginEvent:
        failed_probe = event.fraud_script_type in {"probe_then_drain", "cross_channel_evasion"} and event.amount < 100
        return DeviceLoginEvent(
            event_id=event.event_id,
            timestamp=event.timestamp,
            account_id=event.src_account,
            device_id=event.device_id,
            ip=event.ip,
            geo=event.geo,
            source_channel=event.source_channel,
            login_result="challenge" if failed_probe else "success",
            scenario_id=event.scenario_id,
        )

    def _blacklist_event(self, event: TransactionEvent) -> BlacklistEvent | None:
        if not event.is_scripted_fraud:
            return None
        if event.fraud_script_type in {"device_reuse", "cross_channel_evasion"}:
            entity_type = "device"
            entity_id = event.device_id
        elif event.fraud_script_type in {"ip_cluster", "burst_transfer"}:
            entity_type = "ip"
            entity_id = event.ip
        elif event.fraud_script_type == "merchant_laundering":
            entity_type = "merchant"
            entity_id = event.merchant_id
        else:
            entity_type = "account"
            entity_id = str(event.src_account)
        return BlacklistEvent(
            event_id=event.event_id,
            timestamp=event.timestamp,
            account_id=event.src_account,
            entity_type=entity_type,
            entity_id=entity_id,
            risk_reason=event.fraud_script_type,
            expires_at=event.timestamp + 86_400,
            scenario_id=event.scenario_id,
        )

    def _delayed_label_event(self, event: TransactionEvent) -> DelayedLabelEvent | None:
        if not event.is_scripted_fraud:
            return None
        delay = 1_800 + (event.event_id % 14_400)
        return DelayedLabelEvent(
            event_id=event.event_id,
            timestamp=event.timestamp + delay,
            labeled_event_id=event.event_id,
            label="fraud",
            label_delay_seconds=delay,
            fraud_script_type=event.fraud_script_type,
        )
