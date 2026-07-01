from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Iterable

from ..core.config import APP_CONFIG
from .schemas import TransactionEvent
from .simulator import CHANNELS, FRAUD_TYPES, MultiSourceFraudSimulator, SimulatorConfig


@dataclass(frozen=True, slots=True)
class RealtimeDataSource:
    key: str
    label: str
    description: str
    mode: str
    seed: int
    simulator_config: SimulatorConfig


DATA_SOURCES: dict[str, RealtimeDataSource] = {
    "kafka_live": RealtimeDataSource(
        key="kafka_live",
        label="Kafka 实时链路",
        description="读取 Kafka、Flink、评分服务写入的风险事件库，展示真实实时链路结果。",
        mode="Kafka 实时链路",
        seed=21,
        simulator_config=SimulatorConfig(seed=21, fraud_ratio=0.26, account_count=12_000, merchant_count=420, device_count=6_000),
    ),
    "simulator": RealtimeDataSource(
        key="simulator",
        label="多源仿真流",
        description="持续生成银行转账、钱包支付、商户收单、设备登录和黑名单事件。",
        mode="多源仿真流实时评分",
        seed=42,
        simulator_config=SimulatorConfig(seed=42, fraud_ratio=0.26, account_count=12_000, merchant_count=420, device_count=6_000),
    ),
    "dgraph_replay": RealtimeDataSource(
        key="dgraph_replay",
        label="DGraph 风险先验回放",
        description="使用 DGraph-Fin 风险账户先验驱动实时交易回放，突出图结构风险传播。",
        mode="DGraph 风险先验回放",
        seed=84,
        simulator_config=SimulatorConfig(seed=84, fraud_ratio=0.34, account_count=12_000, merchant_count=360, device_count=5_000),
    ),
    "amlsim_sample": RealtimeDataSource(
        key="amlsim_sample",
        label="AMLSim 样例回放",
        description="从本地 AMLSim 样例交易文件回放账户转账和洗钱模式。",
        mode="AMLSim 样例回放",
        seed=126,
        simulator_config=SimulatorConfig(seed=126, fraud_ratio=0.20, account_count=4_000, merchant_count=180, device_count=1_800),
    ),
    "ieee_cis": RealtimeDataSource(
        key="ieee_cis",
        label="IEEE 交易回放",
        description="从 IEEE-CIS 交易表抽取金额、卡号和欺诈标签，转换为实时交易事件。",
        mode="IEEE 交易回放",
        seed=168,
        simulator_config=SimulatorConfig(seed=168, fraud_ratio=0.18, account_count=16_000, merchant_count=520, device_count=7_000),
    ),
}


def get_data_source(source_key: str | None) -> RealtimeDataSource:
    key = (source_key or "simulator").strip() or "simulator"
    if key not in DATA_SOURCES:
        valid = "、".join(item.label for item in DATA_SOURCES.values())
        raise KeyError(f"未知数据源：{source_key}。可选数据源：{valid}")
    return DATA_SOURCES[key]


def create_simulator(source: RealtimeDataSource) -> MultiSourceFraudSimulator:
    config = _runtime_config(source)
    if source.key == "amlsim_sample":
        return AmlsimReplaySimulator(config, _amlsim_transactions())
    if source.key == "ieee_cis":
        return IeeeReplaySimulator(config, _ieee_transactions())
    return MultiSourceFraudSimulator(config)


def _runtime_config(source: RealtimeDataSource) -> SimulatorConfig:
    return SimulatorConfig(
        account_count=source.simulator_config.account_count,
        merchant_count=source.simulator_config.merchant_count,
        device_count=source.simulator_config.device_count,
        fraud_ratio=source.simulator_config.fraud_ratio,
        seed=source.simulator_config.seed,
        event_id_start=source.simulator_config.event_id_start,
        timestamp_start=int(time.time()),
    )


class ReplaySimulator(MultiSourceFraudSimulator):
    def __init__(self, config: SimulatorConfig, replay_events: list[TransactionEvent]) -> None:
        super().__init__(config)
        if not replay_events:
            raise ValueError("回放数据源没有可用交易事件。")
        self.replay_events = replay_events
        self.replay_index = 0

    def stream(self, event_count: int) -> Iterable[TransactionEvent]:
        for _ in range(event_count):
            template = self.replay_events[self.replay_index % len(self.replay_events)]
            self.replay_index += 1
            event_id = next(self.event_counter)
            yield TransactionEvent(
                event_id=event_id,
                timestamp=self.config.timestamp_start + event_id,
                source_channel=template.source_channel,
                src_account=template.src_account,
                dst_account=template.dst_account,
                amount=template.amount,
                merchant_id=template.merchant_id,
                device_id=template.device_id,
                ip=template.ip,
                geo=template.geo,
                edge_type=template.edge_type,
                scenario_id=template.scenario_id,
                is_scripted_fraud=template.is_scripted_fraud,
                fraud_script_type=template.fraud_script_type,
            )


class AmlsimReplaySimulator(ReplaySimulator):
    pass


class IeeeReplaySimulator(ReplaySimulator):
    pass


def _amlsim_transactions(limit: int = 6_000) -> list[TransactionEvent]:
    sample_dir = APP_CONFIG.dataset_path("amlsim_sample")
    tx_path = sample_dir / "tx.csv"
    alerts_path = sample_dir / "alerts.csv"
    suspicious_accounts = _read_amlsim_alert_accounts(alerts_path)
    events: list[TransactionEvent] = []
    with tx_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            if index >= limit:
                break
            src = int(float(row["ACCOUNT_ID"]))
            dst = int(float(row["COUNTER_PARTY_ACCOUNT_NUM"]))
            tx_type = str(row.get("TXN_SOURCE_TYPE_CODE") or "WIRE").strip().lower()
            scripted = src in suspicious_accounts or dst in suspicious_accounts
            fraud_type = "cycle_transfer" if scripted else "none"
            events.append(
                TransactionEvent(
                    event_id=index,
                    timestamp=int(float(row.get("start") or index)),
                    source_channel=_channel_from_text(tx_type),
                    src_account=src,
                    dst_account=dst,
                    amount=round(float(row.get("TXN_AMOUNT_ORIG") or 0.0), 2),
                    merchant_id=f"m_amlsim_{dst % 240:05d}",
                    device_id=f"d_amlsim_{src % 1200:06d}",
                    ip=f"10.44.{src % 255}.{(dst % 220) + 20}",
                    geo="US-NY",
                    edge_type=1 + (index % 11),
                    scenario_id="amlsim-cycle-alert" if scripted else "amlsim-normal",
                    is_scripted_fraud=scripted,
                    fraud_script_type=fraud_type,
                )
            )
    return events


def _read_amlsim_alert_accounts(path: Path) -> set[int]:
    if not path.exists():
        return set()
    accounts: set[int] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                accounts.add(int(float(row["ACCOUNT_ID"])))
            except (KeyError, TypeError, ValueError):
                continue
    return accounts


def _ieee_transactions(limit: int = 8_000) -> list[TransactionEvent]:
    dataset_dir = APP_CONFIG.dataset_path("ieee_cis")
    tx_path = dataset_dir / "train_transaction.csv"
    events: list[TransactionEvent] = []
    with tx_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            if index >= limit:
                break
            transaction_id = int(float(row["TransactionID"]))
            card = _safe_int(row.get("card1"), transaction_id % 10_000)
            addr = _safe_int(row.get("addr1"), transaction_id % 7_000)
            label = str(row.get("isFraud") or "0") == "1"
            product = str(row.get("ProductCD") or "W").strip()
            events.append(
                TransactionEvent(
                    event_id=index,
                    timestamp=_safe_int(row.get("TransactionDT"), index),
                    source_channel=_ieee_channel(product),
                    src_account=card,
                    dst_account=10_000 + addr,
                    amount=round(float(row.get("TransactionAmt") or 0.0), 2),
                    merchant_id=f"m_ieee_{product.lower()}_{addr % 320:04d}",
                    device_id=f"d_ieee_{card % 5000:06d}",
                    ip=f"10.77.{card % 255}.{(addr % 220) + 20}",
                    geo="US-CA",
                    edge_type=1 + (transaction_id % 11),
                    scenario_id="ieee-labeled-fraud" if label else "ieee-normal",
                    is_scripted_fraud=label,
                    fraud_script_type="card_not_present_fraud" if label else "none",
                )
            )
    return events


def _channel_from_text(value: str) -> str:
    text = value.lower()
    if "wire" in text:
        return "bank_transfer"
    if "credit" in text:
        return "wallet_pay"
    if "check" in text:
        return "merchant_acquire"
    if "deposit" in text:
        return "mobile_banking"
    return CHANNELS[hash(text) % len(CHANNELS)]


def _ieee_channel(product: str) -> str:
    mapping = {
        "W": "wallet_pay",
        "C": "bank_transfer",
        "R": "merchant_acquire",
        "H": "mobile_banking",
        "S": "qr_pay",
    }
    return mapping.get(product.upper(), "wallet_pay")


def _safe_int(value: str | None, fallback: int) -> int:
    try:
        if value is None or value == "":
            return fallback
        return int(float(value))
    except ValueError:
        return fallback
