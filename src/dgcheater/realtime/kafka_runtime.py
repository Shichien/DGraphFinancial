from __future__ import annotations

import socket
import time
from collections.abc import Iterable
from dataclasses import dataclass, fields
from typing import Any, TypeVar

from confluent_kafka import Consumer, KafkaException, Producer

from .event_io import from_json_bytes, to_json_bytes
from .feature_engine import RealtimeFeatureEngine
from .metrics import RuntimeMetricsStore
from .realtime_sinks import Neo4jGraphSink, RealtimeSinkBundle, RedisRiskSink
from .schemas import AccountProfileEvent, BlacklistEvent, DeviceLoginEvent, RealtimeFeatures, RiskDecision, TransactionEvent
from .scoring import FusionRiskScorer
from .simulator import MultiSourceFraudSimulator, SimulatorConfig
from .storage import RiskEventRepository


T = TypeVar("T")


@dataclass(slots=True)
class PendingMultiSourceEvent:
    transaction: TransactionEvent | None = None
    account: AccountProfileEvent | None = None
    device: DeviceLoginEvent | None = None
    blacklist: BlacklistEvent | None = None

    @property
    def has_required_sources(self) -> bool:
        return self.transaction is not None and self.account is not None and self.device is not None


def _dataclass_from_dict(cls: type[T], data: dict[str, Any]) -> T:
    names = {item.name for item in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in names})


class KafkaJsonProducer:
    def __init__(self, bootstrap_servers: str) -> None:
        self.producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "client.id": f"dgcheater-{socket.gethostname()}",
            }
        )

    def send(self, topic: str, key: str, payload: Any) -> None:
        self.producer.produce(topic=topic, key=key, value=to_json_bytes(payload))
        self.producer.poll(0)

    def flush(self) -> None:
        self.producer.flush()


class KafkaJsonConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        auto_offset_reset: str = "latest",
    ) -> None:
        self.consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": auto_offset_reset,
                "enable.auto.commit": True,
            }
        )
        self.consumer.subscribe(topics)

    def records(self) -> Iterable[tuple[str, dict[str, Any]]]:
        try:
            while True:
                message = self.consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    raise KafkaException(message.error())
                yield message.topic(), from_json_bytes(message.value())
        finally:
            self.consumer.close()


def produce_simulated_transactions(
    *,
    bootstrap_servers: str,
    topic: str,
    event_count: int,
    interval_ms: int,
    seed: int,
    event_id_start: int = 0,
    timestamp_start: int = 0,
) -> None:
    simulator = MultiSourceFraudSimulator(
        SimulatorConfig(seed=seed, event_id_start=event_id_start, timestamp_start=timestamp_start)
    )
    producer = KafkaJsonProducer(bootstrap_servers)
    metrics = RuntimeMetricsStore()
    for batch in simulator.multi_source_stream(event_count):
        event = batch.transaction
        producer.send("accounts.raw", str(batch.account.account_id), batch.account)
        producer.send("devices.raw", batch.device.device_id, batch.device)
        if batch.blacklist is not None:
            producer.send("blacklist.raw", batch.blacklist.entity_id, batch.blacklist)
        if batch.delayed_label is not None:
            producer.send("labels.delayed", str(batch.delayed_label.labeled_event_id), batch.delayed_label)
        producer.send(topic, str(event.src_account), event)
        metrics.record_produced(event_timestamp=event.timestamp)
        if interval_ms > 0:
            time.sleep(interval_ms / 1000.0)
    producer.flush()


def run_feature_worker(
    *,
    bootstrap_servers: str,
    input_topic: str,
    output_topic: str,
    group_id: str,
    auto_offset_reset: str = "latest",
) -> None:
    consumer = KafkaJsonConsumer(bootstrap_servers, group_id, [input_topic], auto_offset_reset=auto_offset_reset)
    producer = KafkaJsonProducer(bootstrap_servers)
    engine = RealtimeFeatureEngine()
    metrics = RuntimeMetricsStore()
    for _, item in consumer.records():
        event = _dataclass_from_dict(TransactionEvent, item)
        features = engine.transform(event)
        producer.send(output_topic, str(features.src_account), features)
        metrics.record_feature(event_timestamp=features.timestamp)


def run_multisource_feature_worker(
    *,
    bootstrap_servers: str,
    transaction_topic: str,
    account_topic: str,
    device_topic: str,
    blacklist_topic: str,
    output_topic: str,
    group_id: str,
    auto_offset_reset: str = "latest",
) -> None:
    consumer = KafkaJsonConsumer(
        bootstrap_servers,
        group_id,
        [transaction_topic, account_topic, device_topic, blacklist_topic],
        auto_offset_reset=auto_offset_reset,
    )
    producer = KafkaJsonProducer(bootstrap_servers)
    engine = RealtimeFeatureEngine()
    metrics = RuntimeMetricsStore()
    pending: dict[int, PendingMultiSourceEvent] = {}
    max_seen_event_id = -1
    for topic, item in consumer.records():
        event_id = int(item["event_id"])
        max_seen_event_id = max(max_seen_event_id, event_id)
        batch = pending.setdefault(event_id, PendingMultiSourceEvent())
        if topic == account_topic:
            batch.account = _dataclass_from_dict(AccountProfileEvent, item)
        elif topic == device_topic:
            batch.device = _dataclass_from_dict(DeviceLoginEvent, item)
        elif topic == blacklist_topic:
            batch.blacklist = _dataclass_from_dict(BlacklistEvent, item)
        elif topic == transaction_topic:
            batch.transaction = _dataclass_from_dict(TransactionEvent, item)
        _flush_ready_multisource_events(
            pending=pending,
            max_seen_event_id=max_seen_event_id,
            engine=engine,
            producer=producer,
            output_topic=output_topic,
            metrics=metrics,
        )


def _flush_ready_multisource_events(
    *,
    pending: dict[int, PendingMultiSourceEvent],
    max_seen_event_id: int,
    engine: RealtimeFeatureEngine,
    producer: KafkaJsonProducer,
    output_topic: str,
    metrics: RuntimeMetricsStore,
    grace_event_gap: int = 5,
) -> None:
    ready_cutoff = max_seen_event_id - grace_event_gap
    for event_id in sorted(list(pending)):
        if event_id > ready_cutoff:
            continue
        batch = pending[event_id]
        if not batch.has_required_sources:
            continue
        event = batch.transaction
        if event is None or batch.account is None or batch.device is None:
            continue
        engine.ingest_account(batch.account)
        engine.ingest_device(batch.device)
        if batch.blacklist is not None:
            engine.ingest_blacklist(batch.blacklist)
        features = engine.transform(event)
        producer.send(output_topic, str(features.src_account), features)
        metrics.record_feature(event_timestamp=features.timestamp)
        del pending[event_id]


def run_scoring_worker(
    *,
    bootstrap_servers: str,
    input_topic: str,
    scored_topic: str,
    alerts_topic: str,
    audit_topic: str,
    group_id: str,
    database_url: str | None,
    redis_url: str | None = None,
    neo4j_uri: str | None = None,
    neo4j_user: str = "neo4j",
    neo4j_password: str = "dgcheater",
    auto_offset_reset: str = "latest",
) -> None:
    consumer = KafkaJsonConsumer(bootstrap_servers, group_id, [input_topic], auto_offset_reset=auto_offset_reset)
    producer = KafkaJsonProducer(bootstrap_servers)
    scorer = FusionRiskScorer()
    repository = RiskEventRepository(database_url) if database_url else None
    metrics = RuntimeMetricsStore()
    sinks = RealtimeSinkBundle(
        redis_sink=RedisRiskSink(redis_url) if redis_url else None,
        graph_sink=Neo4jGraphSink(neo4j_uri, neo4j_user, neo4j_password) if neo4j_uri else None,
    )
    try:
        for _, item in consumer.records():
            features = _dataclass_from_dict(RealtimeFeatures, item)
            started = time.perf_counter()
            decision = scorer.score(features)
            scoring_latency_ms = (time.perf_counter() - started) * 1000
            producer.send(scored_topic, str(decision.src_account), decision)
            sinks.write(features, decision)
            if repository is not None:
                repository.upsert_decision(decision)
            metrics.record_scored(
                latency_ms=scoring_latency_ms,
                is_alert=decision.risk_level in {"critical", "high"},
                event_timestamp=decision.timestamp,
            )
            if decision.risk_level in {"critical", "high"}:
                producer.send(alerts_topic, str(decision.src_account), decision)
                producer.send(audit_topic, str(decision.event_id), _audit_payload(decision))
    finally:
        sinks.close()


def _audit_payload(decision: RiskDecision) -> dict[str, Any]:
    return {
        "event_id": decision.event_id,
        "timestamp": decision.timestamp,
        "action": "risk_decision_created",
        "detail": {
            "risk_level": decision.risk_level,
            "decision": decision.decision,
            "reason_codes": decision.reason_codes,
        },
    }
