from __future__ import annotations

import json
from collections import deque
from typing import Any

try:
    from pyflink.common import Configuration, Types, WatermarkStrategy
    from pyflink.common.serialization import SimpleStringSchema
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.datastream.connectors.kafka import KafkaOffsetsInitializer, KafkaRecordSerializationSchema, KafkaSink, KafkaSource
    from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
    from pyflink.datastream.state import ValueStateDescriptor
    from pyflink.datastream.state_backend import EmbeddedRocksDBStateBackend

    PYFLINK_AVAILABLE = True
except ModuleNotFoundError:
    PYFLINK_AVAILABLE = False

    class Types:
        @staticmethod
        def STRING() -> str:
            return "STRING"

    class KeyedProcessFunction:
        pass

    class RuntimeContext:
        pass

    class ValueStateDescriptor:
        def __init__(self, name: str, value_type: Any) -> None:
            self.name = name
            self.value_type = value_type


REQUIRED_FEATURE_PARTS = {
    "account_src",
    "account_dst",
    "device",
    "ip",
    "merchant",
    "blacklist_account_src",
    "blacklist_account_dst",
    "blacklist_device",
    "blacklist_ip",
    "blacklist_merchant",
    "account_profile",
    "device_login",
}


class LocalStringState:
    def __init__(self) -> None:
        self.payload: str | None = None

    def value(self) -> str | None:
        return self.payload

    def update(self, payload: str) -> None:
        self.payload = payload


class EntityFeatureFunction(KeyedProcessFunction):
    def open(self, runtime_context: RuntimeContext) -> None:
        descriptor = ValueStateDescriptor("entity-feature-state", Types.STRING())
        self.state = runtime_context.get_state(descriptor)

    def process_element(self, value: str, ctx: KeyedProcessFunction.Context):
        for output in _process_entity_message(value, self.state):
            yield output


class EventFeatureJoinFunction(KeyedProcessFunction):
    def open(self, runtime_context: RuntimeContext) -> None:
        descriptor = ValueStateDescriptor("event-feature-join-state", Types.STRING())
        self.state = runtime_context.get_state(descriptor)

    def process_element(self, value: str, ctx: KeyedProcessFunction.Context):
        event_state = _load_event_state(self.state.value())
        partial = json.loads(value)
        part_name = str(partial["part"])
        if event_state.get("emitted"):
            return
        event_state["parts"][part_name] = partial["value"]
        if REQUIRED_FEATURE_PARTS.issubset(set(event_state["parts"])):
            for output in _build_joined_outputs(event_state["parts"]):
                yield output
            self.state.update(json.dumps({"emitted": True, "parts": {}}, ensure_ascii=False, separators=(",", ":")))
            return
        self.state.update(json.dumps(event_state, ensure_ascii=False, separators=(",", ":")))


class CleanAndFeatureFunction:
    """Local runner for the same two-stage keyed-state pipeline used by PyFlink."""

    def __init__(self) -> None:
        self.entity_states: dict[str, LocalStringState] = {}
        self.event_states: dict[str, LocalStringState] = {}

    def process_local(self, topic: str, payload: dict[str, Any]) -> list[str]:
        outputs: list[str] = []
        for route in _source_routes(_route(topic, payload)):
            entity_key = _entity_key(route)
            entity_state = self.entity_states.setdefault(entity_key, LocalStringState())
            for partial in _process_entity_message(route, entity_state):
                event_key = _event_key(partial)
                event_state = self.event_states.setdefault(event_key, LocalStringState())
                outputs.extend(_process_event_partial(partial, event_state))
        return outputs

    def flush_local(self) -> list[str]:
        return []


def main() -> None:
    if not PYFLINK_AVAILABLE:
        raise RuntimeError("当前环境缺少 PyFlink。请在 Flink 容器内运行该作业，或使用本地 smoke 验证状态逻辑。")
    config = Configuration()
    config.set_string("pipeline.name", "dgcheater-realtime-features")
    env = StreamExecutionEnvironment.get_execution_environment(config)
    env.set_parallelism(2)
    env.set_state_backend(EmbeddedRocksDBStateBackend())

    transaction_source = _kafka_source("transactions.raw", "dgcheater-flink-feature-job-transactions")
    account_source = _kafka_source("accounts.raw", "dgcheater-flink-feature-job-accounts")
    device_source = _kafka_source("devices.raw", "dgcheater-flink-feature-job-devices")
    blacklist_source = _kafka_source("blacklist.raw", "dgcheater-flink-feature-job-blacklist")
    cleaned_sink = _kafka_sink("transactions.cleaned")
    feature_sink = _kafka_sink("features.realtime")

    stream = env.from_source(transaction_source, WatermarkStrategy.no_watermarks(), "transactions.raw").map(
        lambda item: _wrap_topic("transactions.raw", item),
        output_type=Types.STRING(),
    )
    stream = stream.union(
        env.from_source(account_source, WatermarkStrategy.no_watermarks(), "accounts.raw").map(
            lambda item: _wrap_topic("accounts.raw", item),
            output_type=Types.STRING(),
        ),
        env.from_source(device_source, WatermarkStrategy.no_watermarks(), "devices.raw").map(
            lambda item: _wrap_topic("devices.raw", item),
            output_type=Types.STRING(),
        ),
        env.from_source(blacklist_source, WatermarkStrategy.no_watermarks(), "blacklist.raw").map(
            lambda item: _wrap_topic("blacklist.raw", item),
            output_type=Types.STRING(),
        ),
    )

    routed_entities = stream.flat_map(_source_routes, output_type=Types.STRING())
    partials = routed_entities.key_by(_entity_key, key_type=Types.STRING()).process(
        EntityFeatureFunction(),
        output_type=Types.STRING(),
    )
    routed = partials.key_by(_event_key, key_type=Types.STRING()).process(
        EventFeatureJoinFunction(),
        output_type=Types.STRING(),
    )
    routed.filter(lambda item: json.loads(item)["topic"] == "transactions.cleaned").map(
        lambda item: json.dumps(json.loads(item)["value"], ensure_ascii=False, separators=(",", ":")),
        output_type=Types.STRING(),
    ).sink_to(cleaned_sink)
    routed.filter(lambda item: json.loads(item)["topic"] == "features.realtime").map(
        lambda item: json.dumps(json.loads(item)["value"], ensure_ascii=False, separators=(",", ":")),
        output_type=Types.STRING(),
    ).sink_to(feature_sink)
    env.execute("dgcheater-realtime-features")


def _kafka_source(topic: str, group_id: str) -> KafkaSource:
    return (
        KafkaSource.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_topics(topic)
        .set_group_id(group_id)
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )


def _kafka_sink(topic: str) -> KafkaSink:
    return (
        KafkaSink.builder()
        .set_bootstrap_servers("kafka:9092")
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(topic)
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        )
        .build()
    )


def _process_entity_message(value: str, state: LocalStringState) -> list[str]:
    payload = json.loads(value)
    kind = str(payload["kind"])
    item = payload["value"]
    entity_state = _load_entity_state(state.value())
    outputs: list[str] = []

    if kind == "account_profile":
        account = _clean_account(item)
        entity_state["historical_risk_score"] = float(account["historical_risk_score"])
        entity_state["account_age_days"] = int(account["account_age_days"])
        outputs.append(
            _partial(
                account["event_id"],
                "account_profile",
                {
                    "historical_risk_score": round(float(account["historical_risk_score"]), 4),
                    "account_age_days": int(account["account_age_days"]),
                },
            )
        )
    elif kind == "account_login":
        device = _clean_device(item)
        _append_login_result(entity_state, int(device["timestamp"]), str(device["login_result"]))
        outputs.append(
            _partial(
                device["event_id"],
                "device_login",
                {"login_result": str(device["login_result"]), "timestamp": int(device["timestamp"])},
            )
        )
    elif kind == "device_login":
        device = _clean_device(item)
        _add_unique_list(entity_state["linked_accounts"], int(device["account_id"]), 2000)
    elif kind == "ip_login":
        device = _clean_device(item)
        _add_unique_list(entity_state["linked_accounts"], int(device["account_id"]), 2000)
    elif kind == "blacklist_update":
        entity_state["blacklisted"] = True
    elif kind == "transaction_src":
        event = _clean_event(item)
        outputs.append(_partial(event["event_id"], "account_src", _account_src_features(entity_state, event)))
    elif kind == "transaction_dst":
        event = _clean_event(item)
        outputs.append(_partial(event["event_id"], "account_dst", _account_dst_features(entity_state, event)))
    elif kind == "transaction_device":
        event = _clean_event(item)
        _add_unique_list(entity_state["linked_accounts"], int(event["src_account"]), 2000)
        _add_unique_list(entity_state["linked_accounts"], int(event["dst_account"]), 2000)
        outputs.append(_partial(event["event_id"], "device", {"device_account_count": len(entity_state["linked_accounts"])}))
    elif kind == "transaction_ip":
        event = _clean_event(item)
        _add_unique_list(entity_state["linked_accounts"], int(event["src_account"]), 2000)
        _add_unique_list(entity_state["linked_accounts"], int(event["dst_account"]), 2000)
        outputs.append(_partial(event["event_id"], "ip", {"ip_account_count": len(entity_state["linked_accounts"])}))
    elif kind == "transaction_merchant":
        event = _clean_event(item)
        outputs.append(_partial(event["event_id"], "merchant", _merchant_features(entity_state, event)))
    elif kind.startswith("transaction_blacklist_"):
        event = _clean_event(item)
        part = kind.removeprefix("transaction_")
        outputs.append(_partial(event["event_id"], part, {"blacklist_hit_count": int(bool(entity_state["blacklisted"]))}))

    state.update(json.dumps(entity_state, ensure_ascii=False, separators=(",", ":")))
    return outputs


def _process_event_partial(value: str, state: LocalStringState) -> list[str]:
    event_state = _load_event_state(state.value())
    partial = json.loads(value)
    if event_state.get("emitted"):
        return []
    event_state["parts"][str(partial["part"])] = partial["value"]
    if REQUIRED_FEATURE_PARTS.issubset(set(event_state["parts"])):
        outputs = _build_joined_outputs(event_state["parts"])
        state.update(json.dumps({"emitted": True, "parts": {}}, ensure_ascii=False, separators=(",", ":")))
        return outputs
    state.update(json.dumps(event_state, ensure_ascii=False, separators=(",", ":")))
    return []


def _source_routes(item: str) -> list[str]:
    envelope = json.loads(item)
    topic = str(envelope["topic"])
    payload = envelope["value"]
    if topic == "transactions.raw":
        event = _clean_event(payload)
        src = int(event["src_account"])
        dst = int(event["dst_account"])
        return [
            _entity_route(f"account:{src}", "transaction_src", event),
            _entity_route(f"account:{dst}", "transaction_dst", event),
            _entity_route(f"device:{event['device_id']}", "transaction_device", event),
            _entity_route(f"ip:{event['ip']}", "transaction_ip", event),
            _entity_route(f"merchant:{event['merchant_id']}", "transaction_merchant", event),
            _entity_route(f"blacklist:account:{src}", "transaction_blacklist_account_src", event),
            _entity_route(f"blacklist:account:{dst}", "transaction_blacklist_account_dst", event),
            _entity_route(f"blacklist:device:{event['device_id']}", "transaction_blacklist_device", event),
            _entity_route(f"blacklist:ip:{event['ip']}", "transaction_blacklist_ip", event),
            _entity_route(f"blacklist:merchant:{event['merchant_id']}", "transaction_blacklist_merchant", event),
        ]
    if topic == "accounts.raw":
        account = _clean_account(payload)
        return [_entity_route(f"account:{account['account_id']}", "account_profile", account)]
    if topic == "devices.raw":
        device = _clean_device(payload)
        return [
            _entity_route(f"account:{device['account_id']}", "account_login", device),
            _entity_route(f"device:{device['device_id']}", "device_login", device),
            _entity_route(f"ip:{device['ip']}", "ip_login", device),
        ]
    if topic == "blacklist.raw":
        blacklist = _clean_blacklist(payload)
        return [
            _entity_route(
                f"blacklist:{blacklist['entity_type']}:{blacklist['entity_id']}",
                "blacklist_update",
                blacklist,
            )
        ]
    return []


def _account_src_features(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    timestamp = int(event["timestamp"])
    dst_account = int(event["dst_account"])
    seconds_since_last = 0
    if state["last_timestamp"] is not None:
        seconds_since_last = max(timestamp - int(state["last_timestamp"]), 0)

    events = [item for item in state["events"] if timestamp - int(item["timestamp"]) <= 600]
    events.append(event)
    state["events"] = events[-2000:]
    channels = [*state["channels"], str(event["source_channel"])]
    state["channels"] = channels[-40:]
    _add_unique_list(state["neighbors"], dst_account, 2000)
    if bool(event["is_scripted_fraud"]):
        _add_unique_list(state["risky_neighbors"], dst_account, 2000)
    state["out_degree"] = int(state["out_degree"]) + 1
    state["last_timestamp"] = timestamp

    src_1m_events = _recent_events(state["events"], timestamp, 60)
    src_5m_amount = sum(float(item["amount"]) for item in state["events"] if timestamp - int(item["timestamp"]) <= 300)
    src_10m_counterparties = {
        int(item["dst_account"])
        for item in state["events"]
        if timestamp - int(item["timestamp"]) <= 600
    }
    channel_switch_count = sum(1 for prev, cur in zip(state["channels"], state["channels"][1:]) if prev != cur)
    recent_login_challenge_count = sum(
        1
        for login_timestamp, login_result in state["login_results"]
        if login_result == "challenge" and timestamp - int(login_timestamp) <= 600
    )
    burst_score = min(len(src_1m_events) / 12.0 + float(event["amount"]) / 150_000.0, 1.0)
    neighbors = [int(item) for item in state["neighbors"]]
    return {
        "event": event,
        "src_1m_count": len(src_1m_events),
        "src_5m_amount": round(src_5m_amount, 2),
        "src_10m_counterparty_count": len(src_10m_counterparties),
        "src_out_degree": int(state["out_degree"]),
        "seconds_since_last_src_event": seconds_since_last,
        "channel_switch_count": channel_switch_count,
        "burst_score": burst_score,
        "graph_neighbor_count": len(neighbors),
        "graph_risky_neighbor_count": len(state["risky_neighbors"]),
        "graph_component_size": min(1 + len(neighbors), 120),
        "graph_community_id": f"comm-{min([int(event['src_account']), *neighbors]) if neighbors else int(event['src_account'])}",
        "graph_related_nodes": sorted(neighbors)[:80],
        "historical_risk_score": round(float(state["historical_risk_score"]), 4),
        "account_age_days": int(state["account_age_days"]),
        "recent_login_challenge_count": recent_login_challenge_count,
    }


def _account_dst_features(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    _add_unique_list(state["neighbors"], int(event["src_account"]), 2000)
    if bool(event["is_scripted_fraud"]):
        _add_unique_list(state["risky_neighbors"], int(event["src_account"]), 2000)
    state["in_degree"] = int(state["in_degree"]) + 1
    return {"dst_in_degree": int(state["in_degree"])}


def _merchant_features(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    timestamp = int(event["timestamp"])
    events = [
        item
        for item in state["amount_events"]
        if timestamp - int(item[0]) <= 300
    ]
    events.append((timestamp, float(event["amount"])))
    state["amount_events"] = events[-2000:]
    return {"merchant_in_amount": round(sum(float(item[1]) for item in state["amount_events"]), 2)}


def _build_joined_outputs(parts: dict[str, dict[str, Any]]) -> list[str]:
    account_src = parts["account_src"]
    event = account_src["event"]
    device_account_count = int(parts["device"]["device_account_count"])
    ip_account_count = int(parts["ip"]["ip_account_count"])
    merchant_in_amount = float(parts["merchant"]["merchant_in_amount"])
    account_profile = parts["account_profile"]
    device_login = parts["device_login"]
    recent_login_challenge_count = max(
        int(account_src["recent_login_challenge_count"]),
        int(str(device_login["login_result"]) == "challenge"),
    )
    blacklist_hit_count = sum(
        int(parts[name]["blacklist_hit_count"])
        for name in (
            "blacklist_account_src",
            "blacklist_account_dst",
            "blacklist_device",
            "blacklist_ip",
            "blacklist_merchant",
        )
    )
    script_score = _script_pattern_score(
        amount=float(event["amount"]),
        src_1m_count=int(account_src["src_1m_count"]),
        src_5m_amount=float(account_src["src_5m_amount"]),
        counterparty_count=int(account_src["src_10m_counterparty_count"]),
        device_account_count=device_account_count,
        ip_account_count=ip_account_count,
        merchant_in_amount=merchant_in_amount,
        channel_switch_count=int(account_src["channel_switch_count"]),
        graph_neighbor_count=int(account_src["graph_neighbor_count"]),
        graph_component_size=int(account_src["graph_component_size"]),
    )
    features = {
        "event_id": int(event["event_id"]),
        "timestamp": int(event["timestamp"]),
        "src_account": int(event["src_account"]),
        "dst_account": int(event["dst_account"]),
        "amount": float(event["amount"]),
        "source_channel": str(event["source_channel"]),
        "device_id": str(event["device_id"]),
        "ip": str(event["ip"]),
        "merchant_id": str(event["merchant_id"]),
        "edge_type": int(event["edge_type"]),
        "scenario_id": str(event["scenario_id"]),
        "fraud_script_type": str(event["fraud_script_type"]),
        "is_scripted_fraud": bool(event["is_scripted_fraud"]),
        "src_1m_count": int(account_src["src_1m_count"]),
        "src_5m_amount": float(account_src["src_5m_amount"]),
        "src_10m_counterparty_count": int(account_src["src_10m_counterparty_count"]),
        "device_account_count": device_account_count,
        "ip_account_count": ip_account_count,
        "merchant_in_amount": merchant_in_amount,
        "src_out_degree": int(account_src["src_out_degree"]),
        "dst_in_degree": int(parts["account_dst"]["dst_in_degree"]),
        "seconds_since_last_src_event": int(account_src["seconds_since_last_src_event"]),
        "channel_switch_count": int(account_src["channel_switch_count"]),
        "burst_score": float(account_src["burst_score"]),
        "graph_neighbor_count": int(account_src["graph_neighbor_count"]),
        "graph_risky_neighbor_count": int(account_src["graph_risky_neighbor_count"]),
        "graph_component_size": int(account_src["graph_component_size"]),
        "graph_community_id": str(account_src["graph_community_id"]),
        "graph_related_nodes": [int(item) for item in account_src["graph_related_nodes"]],
        "historical_risk_score": round(float(account_profile["historical_risk_score"]), 4),
        "account_age_days": int(account_profile["account_age_days"]),
        "recent_login_challenge_count": recent_login_challenge_count,
        "blacklist_hit_count": blacklist_hit_count,
        "script_score": script_score,
    }
    return [_route("transactions.cleaned", event), _route("features.realtime", features)]


def _load_entity_state(payload: str | None) -> dict[str, Any]:
    if not payload:
        return {
            "events": [],
            "channels": [],
            "login_results": [],
            "historical_risk_score": 0.0,
            "account_age_days": 0,
            "last_timestamp": None,
            "in_degree": 0,
            "out_degree": 0,
            "neighbors": [],
            "risky_neighbors": [],
            "linked_accounts": [],
            "amount_events": [],
            "blacklisted": False,
        }
    data = json.loads(payload)
    data["events"] = [dict(item) for item in data.get("events", [])]
    data["channels"] = [str(item) for item in data.get("channels", [])]
    data["login_results"] = [(int(item[0]), str(item[1])) for item in data.get("login_results", [])]
    data["historical_risk_score"] = float(data.get("historical_risk_score", 0.0))
    data["account_age_days"] = int(data.get("account_age_days", 0))
    data["last_timestamp"] = None if data.get("last_timestamp") is None else int(data["last_timestamp"])
    data["in_degree"] = int(data.get("in_degree", 0))
    data["out_degree"] = int(data.get("out_degree", 0))
    data["neighbors"] = [int(item) for item in data.get("neighbors", [])]
    data["risky_neighbors"] = [int(item) for item in data.get("risky_neighbors", [])]
    data["linked_accounts"] = [int(item) for item in data.get("linked_accounts", [])]
    data["amount_events"] = [(int(item[0]), float(item[1])) for item in data.get("amount_events", [])]
    data["blacklisted"] = bool(data.get("blacklisted", False))
    return data


def _load_event_state(payload: str | None) -> dict[str, Any]:
    if not payload:
        return {"emitted": False, "parts": {}}
    data = json.loads(payload)
    return {"emitted": bool(data.get("emitted", False)), "parts": dict(data.get("parts", {}))}


def _entity_route(entity_key: str, kind: str, value: dict[str, Any]) -> str:
    return json.dumps(
        {"entity_key": entity_key, "kind": kind, "event_id": int(value["event_id"]), "value": value},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _partial(event_id: int, part: str, value: dict[str, Any]) -> str:
    return json.dumps({"event_id": int(event_id), "part": part, "value": value}, ensure_ascii=False, separators=(",", ":"))


def _entity_key(item: str) -> str:
    return str(json.loads(item)["entity_key"])


def _event_key(item: str) -> str:
    return str(json.loads(item)["event_id"])


def _route(topic: str, value: dict[str, Any]) -> str:
    return json.dumps({"topic": topic, "value": value}, ensure_ascii=False, separators=(",", ":"))


def _wrap_topic(topic: str, value: str) -> str:
    return _route(topic, json.loads(value))


def _clean_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": int(event["event_id"]),
        "timestamp": int(event["timestamp"]),
        "source_channel": str(event["source_channel"]).strip() or "unknown",
        "src_account": int(event["src_account"]),
        "dst_account": int(event["dst_account"]),
        "amount": round(max(float(event["amount"]), 0.0), 2),
        "merchant_id": str(event["merchant_id"]).strip() or "merchant_unknown",
        "device_id": str(event["device_id"]).strip() or "device_unknown",
        "ip": str(event["ip"]).strip() or "0.0.0.0",
        "geo": str(event["geo"]).strip() or "unknown",
        "edge_type": int(event["edge_type"]),
        "scenario_id": str(event["scenario_id"]),
        "is_scripted_fraud": bool(event["is_scripted_fraud"]),
        "fraud_script_type": str(event["fraud_script_type"]),
    }


def _clean_account(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": int(event["event_id"]),
        "timestamp": int(event["timestamp"]),
        "account_id": int(event["account_id"]),
        "account_age_days": max(int(event["account_age_days"]), 0),
        "historical_risk_score": min(max(float(event["historical_risk_score"]), 0.0), 1.0),
        "home_geo": str(event["home_geo"]).strip() or "unknown",
        "segment": str(event["segment"]).strip() or "unknown",
        "scenario_id": str(event["scenario_id"]),
    }


def _clean_device(event: dict[str, Any]) -> dict[str, Any]:
    login_result = str(event["login_result"])
    return {
        "event_id": int(event["event_id"]),
        "timestamp": int(event["timestamp"]),
        "account_id": int(event["account_id"]),
        "device_id": str(event["device_id"]).strip() or "device_unknown",
        "ip": str(event["ip"]).strip() or "0.0.0.0",
        "geo": str(event["geo"]).strip() or "unknown",
        "source_channel": str(event["source_channel"]).strip() or "unknown",
        "login_result": login_result if login_result in {"success", "challenge"} else "success",
        "scenario_id": str(event["scenario_id"]),
    }


def _clean_blacklist(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": int(event["event_id"]),
        "timestamp": int(event["timestamp"]),
        "account_id": int(event["account_id"]),
        "entity_type": str(event["entity_type"]),
        "entity_id": str(event["entity_id"]),
        "risk_reason": str(event["risk_reason"]),
        "expires_at": int(event["expires_at"]),
        "scenario_id": str(event["scenario_id"]),
    }


def _append_login_result(state: dict[str, Any], timestamp: int, login_result: str) -> None:
    results = [
        item
        for item in state["login_results"]
        if timestamp - int(item[0]) <= 600
    ]
    results.append((timestamp, login_result))
    state["login_results"] = results[-200:]


def _add_unique_list(items: list[Any], value: Any, limit: int) -> None:
    if value not in items:
        items.append(value)
    if len(items) > limit:
        del items[: len(items) - limit]


def _recent_events(events: list[dict[str, Any]], timestamp: int, window: int) -> list[dict[str, Any]]:
    return [item for item in events if timestamp - int(item["timestamp"]) <= window]


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


if __name__ == "__main__":
    main()
