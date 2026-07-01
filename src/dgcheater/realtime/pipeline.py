from __future__ import annotations

import json
import os
import shutil
import subprocess
import importlib.util
import sys
from dataclasses import asdict
from pathlib import Path

import typer

from .feature_engine import RealtimeFeatureEngine
from .dashboard_api import DemoRuntime, _edges_from_events, _event_from_db, _snapshot_from_runtime
from .kafka_runtime import (
    PendingMultiSourceEvent,
    _flush_ready_multisource_events,
    produce_simulated_transactions,
    run_multisource_feature_worker,
    run_scoring_worker,
)
from .e2e_check import run_e2e_check
from .schema_validation import load_schema, validate_json_schema_sample
from .scoring import SCORE_WEIGHTS, FusionRiskScorer
from .simulator import MultiSourceFraudSimulator, SimulatorConfig


app = typer.Typer(no_args_is_help=True)


@app.callback()
def realtime() -> None:
    """Realtime anti-fraud platform commands."""


@app.command("smoke")
def smoke(event_count: int = 1_000, output_path: Path | None = None) -> None:
    simulator = MultiSourceFraudSimulator(SimulatorConfig())
    feature_engine = RealtimeFeatureEngine()
    scorer = FusionRiskScorer()
    level_counts: dict[str, int] = {}
    decisions: list[dict[str, object]] = []
    for event in simulator.stream(event_count):
        features = feature_engine.transform(event)
        decision = scorer.score(features)
        level_counts[decision.risk_level] = level_counts.get(decision.risk_level, 0) + 1
        if decision.risk_level in {"critical", "high"}:
            decisions.append(decision.to_dict())

    result = {
        "event_count": event_count,
        "risk_level_counts": level_counts,
        "high_or_above_count": len(decisions),
        "sample_alerts": decisions[:8],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("train-realtime-model")
def train_realtime_model(
    event_count: int = 20_000,
    seed: int = 42,
    output_dir: Path | None = None,
) -> None:
    """Train the legacy realtime offline model used before DGraph prior integration."""
    from .offline_model import default_model_dir, train_realtime_offline_model

    output_dir = output_dir or default_model_dir()
    metadata = train_realtime_offline_model(output_dir=output_dir, event_count=event_count, seed=seed)
    typer.echo(json.dumps({"model_dir": str(output_dir), **asdict(metadata)}, ensure_ascii=False, indent=2))


@app.command("multisource-score-smoke")
def multisource_score_smoke(event_count: int = 1_000, seed: int = 42, output_path: Path | None = None) -> None:
    """Run local multi-source ingestion, feature computation and risk scoring without Docker."""
    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    feature_engine = RealtimeFeatureEngine()
    scorer = FusionRiskScorer()
    level_counts: dict[str, int] = {}
    blacklist_feature_hits = 0
    challenge_feature_hits = 0
    historical_risk_hits = 0
    alert_samples: list[dict[str, object]] = []
    for batch in simulator.multi_source_stream(event_count):
        feature_engine.ingest_account(batch.account)
        feature_engine.ingest_device(batch.device)
        if batch.blacklist is not None:
            feature_engine.ingest_blacklist(batch.blacklist)
        features = feature_engine.transform(batch.transaction)
        decision = scorer.score(features)
        level_counts[decision.risk_level] = level_counts.get(decision.risk_level, 0) + 1
        blacklist_feature_hits += int(features.blacklist_hit_count > 0)
        challenge_feature_hits += int(features.recent_login_challenge_count > 0)
        historical_risk_hits += int(features.historical_risk_score >= 0.55)
        if decision.risk_level in {"critical", "high"} and len(alert_samples) < 8:
            alert_samples.append(decision.to_dict())

    result = {
        "event_count": event_count,
        "risk_level_counts": level_counts,
        "blacklist_feature_hits": blacklist_feature_hits,
        "challenge_feature_hits": challenge_feature_hits,
        "historical_risk_hits": historical_risk_hits,
        "sample_alerts": alert_samples,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("graph-trace-smoke")
def graph_trace_smoke(event_count: int = 1_000, seed: int = 42, output_path: Path | None = None) -> None:
    """Verify that scored alerts contain graph community and neighborhood evidence."""
    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    feature_engine = RealtimeFeatureEngine()
    scorer = FusionRiskScorer()
    alert_count = 0
    max_related_nodes = 0
    total_related_nodes = 0
    communities: dict[str, int] = {}
    samples: list[dict[str, object]] = []
    for batch in simulator.multi_source_stream(event_count):
        feature_engine.ingest_account(batch.account)
        feature_engine.ingest_device(batch.device)
        if batch.blacklist is not None:
            feature_engine.ingest_blacklist(batch.blacklist)
        features = feature_engine.transform(batch.transaction)
        decision = scorer.score(features)
        if decision.risk_level not in {"critical", "high"}:
            continue
        alert_count += 1
        related_count = len(decision.related_nodes)
        total_related_nodes += related_count
        max_related_nodes = max(max_related_nodes, related_count)
        communities[decision.community_id] = communities.get(decision.community_id, 0) + 1
        if len(samples) < 8:
            samples.append(
                {
                    "event_id": decision.event_id,
                    "risk_score": decision.risk_score,
                    "risk_level": decision.risk_level,
                    "community_id": decision.community_id,
                    "related_node_count": related_count,
                    "related_nodes": decision.related_nodes[:20],
                    "reason_codes": decision.reason_codes,
                    "evidence": decision.evidence,
                }
            )

    result = {
        "event_count": event_count,
        "alert_count": alert_count,
        "avg_related_nodes": round(total_related_nodes / alert_count, 2) if alert_count else 0.0,
        "max_related_nodes": max_related_nodes,
        "community_count": len(communities),
        "top_communities": dict(sorted(communities.items(), key=lambda item: (-item[1], item[0]))[:8]),
        "samples": samples,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("dashboard-contract-smoke")
def dashboard_contract_smoke(event_count: int = 1_000, seed: int = 42, output_path: Path | None = None) -> None:
    """Verify dashboard payloads expose explanations, related nodes and trace edges."""
    runtime = DemoRuntime(simulator=MultiSourceFraudSimulator(SimulatorConfig(seed=seed)))
    runtime.advance(event_count)
    snapshot = _snapshot_from_runtime(runtime)
    events = snapshot["recentEvents"]
    events_with_reasons = sum(1 for event in events if event.get("reasonCodes"))
    events_with_related_nodes = sum(1 for event in events if len(event.get("relatedNodes", [])) > 2)
    related_edges = sum(1 for edge in snapshot["edges"] if edge.get("sourceScope") == "related")

    db_event = _event_from_db(
        {
            "event_id": 900_001,
            "event_time": 1_234,
            "src_account": 100,
            "dst_account": 200,
            "risk_score": 0.83,
            "risk_level": "critical",
            "decision": "block",
            "community_id": "comm-100",
            "evidence_json": {
                "amount": 120_000,
                "source_channel": "wallet_pay",
                "graph_neighbor_count": 4,
                "offline_model_score": 0.7,
                "realtime_behavior_score": 0.8,
                "graph_community_score": 0.9,
                "rule_score": 1.0,
            },
            "reason_codes": ["blacklist:hit", "rule:multi-hit"],
            "related_edges": [
                {"event_id": 900_001, "src_account": 100, "dst_account": 300, "relation_type": "related_node"},
                {"event_id": 900_001, "src_account": 100, "dst_account": 400, "relation_type": "related_node"},
            ],
            "related_nodes": [100, 200, 300, 400],
        }
    )
    db_edges = _edges_from_events([db_event])
    result = {
        "event_count": event_count,
        "window_event_count": len(events),
        "summary": snapshot["summary"],
        "events_with_reasons": events_with_reasons,
        "events_with_related_nodes": events_with_related_nodes,
        "related_edges": related_edges,
        "db_event_reason_count": len(db_event["reasonCodes"]),
        "db_event_related_node_count": len(db_event["relatedNodes"]),
        "db_event_edge_count": len(db_edges),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("scoring-contract-smoke")
def scoring_contract_smoke(output_path: Path | None = None) -> None:
    """Verify risk score and dashboard explanation use the same fusion weights."""
    scorer = FusionRiskScorer()
    expected_weights = {
        "offline_model_score": 0.45,
        "realtime_behavior_score": 0.30,
        "graph_community_score": 0.15,
        "rule_score": 0.10,
    }
    mismatches = {
        key: {"expected": expected, "actual": SCORE_WEIGHTS.get(key)}
        for key, expected in expected_weights.items()
        if SCORE_WEIGHTS.get(key) != expected
    }
    total_weight = round(sum(SCORE_WEIGHTS.values()), 10)
    result = {
        "ok": not mismatches and total_weight == 1.0,
        "weights": SCORE_WEIGHTS,
        "expected_weights": expected_weights,
        "total_weight": total_weight,
        "mismatches": mismatches,
        "offline_model_name": scorer.account_prior.metadata.model_name,
        "offline_model_dataset": scorer.account_prior.metadata.dataset_key,
        "offline_model_feature_count": scorer.account_prior.metadata.feature_count,
        "offline_model_valid_auc": scorer.account_prior.metadata.valid_auc,
        "offline_model_node_count": scorer.account_prior.metadata.node_count,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise typer.Exit(code=1)


@app.command("dgraph-prior-smoke")
def dgraph_prior_smoke(event_count: int = 200, seed: int = 42, output_path: Path | None = None) -> None:
    """Verify realtime scoring uses the DGraph-Fin model as account prior."""
    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    feature_engine = RealtimeFeatureEngine()
    scorer = FusionRiskScorer()
    samples: list[dict[str, object]] = []
    score_values: list[float] = []
    for batch in simulator.multi_source_stream(event_count):
        feature_engine.ingest_account(batch.account)
        feature_engine.ingest_device(batch.device)
        if batch.blacklist is not None:
            feature_engine.ingest_blacklist(batch.blacklist)
        features = feature_engine.transform(batch.transaction)
        decision = scorer.score(features)
        offline_score = float(decision.evidence["offline_model_score"])
        score_values.append(offline_score)
        if len(samples) < 6:
            samples.append(
                {
                    "event_id": decision.event_id,
                    "src_account": decision.src_account,
                    "dst_account": decision.dst_account,
                    "offline_model_score": offline_score,
                    "dgraph_src_account_score": decision.evidence["dgraph_src_account_score"],
                    "dgraph_dst_account_score": decision.evidence["dgraph_dst_account_score"],
                    "dgraph_src_node_id": decision.evidence["dgraph_src_node_id"],
                    "dgraph_dst_node_id": decision.evidence["dgraph_dst_node_id"],
                    "risk_score": decision.risk_score,
                    "risk_level": decision.risk_level,
                }
            )
    result = {
        "ok": bool(score_values) and len(set(round(item, 6) for item in score_values)) > 1,
        "event_count": event_count,
        "model_name": scorer.account_prior.metadata.model_name,
        "dataset": scorer.account_prior.metadata.dataset_key,
        "node_count": scorer.account_prior.metadata.node_count,
        "feature_count": scorer.account_prior.metadata.feature_count,
        "valid_auc": scorer.account_prior.metadata.valid_auc,
        "min_offline_model_score": min(score_values) if score_values else 0.0,
        "max_offline_model_score": max(score_values) if score_values else 0.0,
        "samples": samples,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise typer.Exit(code=1)


@app.command("flink-local-smoke")
def flink_local_smoke(event_count: int = 1_000, seed: int = 42, output_path: Path | None = None) -> None:
    """Run the PyFlink feature function locally to verify multi-source state logic."""
    repo_root = Path(__file__).resolve().parents[3]
    job_path = repo_root / "flink" / "jobs" / "realtime_features.py"
    spec = importlib.util.spec_from_file_location("dgcheater_flink_realtime_features", job_path)
    if spec is None or spec.loader is None:
        raise typer.BadParameter(f"无法加载 Flink 作业文件：{job_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    CleanAndFeatureFunction = module.CleanAndFeatureFunction

    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    function = CleanAndFeatureFunction()
    counters = {
        "feature_count": 0,
        "cleaned_count": 0,
        "historical_risk_hits": 0,
        "challenge_hits": 0,
        "blacklist_hits": 0,
    }
    samples: list[dict[str, object]] = []

    def collect_outputs(outputs: list[str]) -> None:
        for item in outputs:
            record = json.loads(item)
            if record["topic"] == "transactions.cleaned":
                counters["cleaned_count"] += 1
                continue
            if record["topic"] != "features.realtime":
                continue
            counters["feature_count"] += 1
            feature = record["value"]
            counters["historical_risk_hits"] += int(float(feature["historical_risk_score"]) > 0)
            counters["challenge_hits"] += int(int(feature["recent_login_challenge_count"]) > 0)
            counters["blacklist_hits"] += int(int(feature["blacklist_hit_count"]) > 0)
            if len(samples) < 5 and (
                int(feature["blacklist_hit_count"]) > 0
                or int(feature["recent_login_challenge_count"]) > 0
                or float(feature["historical_risk_score"]) > 0
            ):
                samples.append(
                    {
                        "event_id": int(feature["event_id"]),
                        "historical_risk_score": float(feature["historical_risk_score"]),
                        "account_age_days": int(feature["account_age_days"]),
                        "recent_login_challenge_count": int(feature["recent_login_challenge_count"]),
                        "blacklist_hit_count": int(feature["blacklist_hit_count"]),
                        "device_account_count": int(feature["device_account_count"]),
                        "ip_account_count": int(feature["ip_account_count"]),
                    }
                )

    def feature_outputs(outputs: list[str]) -> list[dict[str, object]]:
        return [
            json.loads(item)["value"]
            for item in outputs
            if json.loads(item)["topic"] == "features.realtime"
        ]

    for batch in simulator.multi_source_stream(event_count):
        collect_outputs(function.process_local("accounts.raw", batch.account.to_dict()))
        collect_outputs(function.process_local("devices.raw", batch.device.to_dict()))
        if batch.blacklist is not None:
            collect_outputs(function.process_local("blacklist.raw", batch.blacklist.to_dict()))
        collect_outputs(function.process_local("transactions.raw", batch.transaction.to_dict()))
    collect_outputs(function.flush_local())

    partition_function = CleanAndFeatureFunction()
    shared_features: list[dict[str, object]] = []
    shared_inputs = [
        {
            "event_id": 990_001,
            "timestamp": 990_001,
            "src_account": 11,
            "dst_account": 21,
            "amount": 10_000.0,
            "source_channel": "wallet_pay",
            "device_id": "d_shared_partition",
            "ip": "172.31.250.10",
            "merchant_id": "m_shared_partition",
        },
        {
            "event_id": 990_002,
            "timestamp": 990_020,
            "src_account": 12,
            "dst_account": 22,
            "amount": 20_000.0,
            "source_channel": "qr_pay",
            "device_id": "d_shared_partition",
            "ip": "172.31.250.10",
            "merchant_id": "m_shared_partition",
        },
    ]
    for item in shared_inputs:
        account_payload = {
            "event_id": item["event_id"],
            "timestamp": item["timestamp"],
            "account_id": item["src_account"],
            "account_age_days": 180,
            "historical_risk_score": 0.61,
            "home_geo": "CN-SH",
            "segment": "retail",
            "scenario_id": "partition-state-smoke",
        }
        device_payload = {
            "event_id": item["event_id"],
            "timestamp": item["timestamp"],
            "account_id": item["src_account"],
            "device_id": item["device_id"],
            "ip": item["ip"],
            "geo": "CN-SH",
            "source_channel": item["source_channel"],
            "login_result": "success",
            "scenario_id": "partition-state-smoke",
        }
        transaction_payload = {
            "event_id": item["event_id"],
            "timestamp": item["timestamp"],
            "source_channel": item["source_channel"],
            "src_account": item["src_account"],
            "dst_account": item["dst_account"],
            "amount": item["amount"],
            "merchant_id": item["merchant_id"],
            "device_id": item["device_id"],
            "ip": item["ip"],
            "geo": "CN-SH",
            "edge_type": 1,
            "scenario_id": "partition-state-smoke",
            "is_scripted_fraud": True,
            "fraud_script_type": "device_reuse",
        }
        partition_function.process_local("accounts.raw", account_payload)
        partition_function.process_local("devices.raw", device_payload)
        shared_features.extend(feature_outputs(partition_function.process_local("transactions.raw", transaction_payload)))

    partition_state_ok = bool(
        shared_features
        and int(shared_features[-1]["device_account_count"]) == 4
        and int(shared_features[-1]["ip_account_count"]) == 4
        and float(shared_features[-1]["merchant_in_amount"]) == 30_000.0
    )

    result = {
        "event_count": event_count,
        **counters,
        "partition_state_ok": partition_state_ok,
        "partition_state_sample": shared_features[-1] if shared_features else {},
        "samples": samples,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if counters["feature_count"] != event_count or counters["cleaned_count"] != event_count or not partition_state_ok:
        raise typer.Exit(code=1)


@app.command("multisource-join-smoke")
def multisource_join_smoke(event_count: int = 1_000, seed: int = 42, output_path: Path | None = None) -> None:
    """Verify Kafka feature worker joins multi-topic events by event_id before scoring features."""

    class MemoryProducer:
        def __init__(self) -> None:
            self.records: list[dict[str, object]] = []

        def send(self, topic: str, key: str, payload: object) -> None:
            self.records.append({"topic": topic, "key": key, "payload": payload})

    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    engine = RealtimeFeatureEngine()
    producer = MemoryProducer()
    metrics = _MemoryMetrics()
    pending: dict[int, PendingMultiSourceEvent] = {}
    max_seen_event_id = -1
    blacklist_expected = 0
    for batch in simulator.multi_source_stream(event_count):
        event_id = batch.transaction.event_id
        max_seen_event_id = max(max_seen_event_id, event_id)
        if batch.blacklist is not None:
            blacklist_expected += 1
        pending[event_id] = PendingMultiSourceEvent(
            transaction=batch.transaction,
            account=batch.account,
            device=batch.device,
            blacklist=batch.blacklist,
        )
        _flush_ready_multisource_events(
            pending=pending,
            max_seen_event_id=max_seen_event_id,
            engine=engine,
            producer=producer,  # type: ignore[arg-type]
            output_topic="features.realtime",
            metrics=metrics,  # type: ignore[arg-type]
        )
    _flush_ready_multisource_events(
        pending=pending,
        max_seen_event_id=max_seen_event_id + 5,
        engine=engine,
        producer=producer,  # type: ignore[arg-type]
        output_topic="features.realtime",
        metrics=metrics,  # type: ignore[arg-type]
    )
    features = [record["payload"] for record in producer.records]
    result = {
        "event_count": event_count,
        "feature_count": len(features),
        "pending_count": len(pending),
        "historical_risk_hits": sum(1 for item in features if getattr(item, "historical_risk_score") > 0),
        "challenge_hits": sum(1 for item in features if getattr(item, "recent_login_challenge_count") > 0),
        "blacklist_expected": blacklist_expected,
        "blacklist_hits": sum(1 for item in features if getattr(item, "blacklist_hit_count") > 0),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


class _MemoryMetrics:
    def __init__(self) -> None:
        self.feature_events: list[int] = []

    def record_feature(self, event_timestamp: int) -> None:
        self.feature_events.append(event_timestamp)


def _ensure_realtime_model() -> None:
    from .offline_model import default_model_dir, train_realtime_offline_model

    model_dir = Path(os.getenv("DG_REALTIME_MODEL_DIR", "")) if os.getenv("DG_REALTIME_MODEL_DIR") else default_model_dir()
    required = [model_dir / "metadata.json", model_dir / "xgboost.joblib", model_dir / "lightgbm_aux.joblib"]
    if all(path.exists() for path in required):
        return
    train_realtime_offline_model(output_dir=model_dir, event_count=20_000, seed=42)


@app.command("multisource-smoke")
def multisource_smoke(event_count: int = 200, seed: int = 42, output_path: Path | None = None) -> None:
    """Verify that the simulator emits all local realtime source streams."""
    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    counts = {
        "transactions.raw": 0,
        "accounts.raw": 0,
        "devices.raw": 0,
        "blacklist.raw": 0,
        "labels.delayed": 0,
    }
    fraud_scripts: dict[str, int] = {}
    samples: dict[str, object] = {}
    for batch in simulator.multi_source_stream(event_count):
        counts["transactions.raw"] += 1
        counts["accounts.raw"] += 1
        counts["devices.raw"] += 1
        samples.setdefault("transactions.raw", batch.transaction.to_dict())
        samples.setdefault("accounts.raw", batch.account.to_dict())
        samples.setdefault("devices.raw", batch.device.to_dict())
        if batch.blacklist is not None:
            counts["blacklist.raw"] += 1
            samples.setdefault("blacklist.raw", batch.blacklist.to_dict())
        if batch.delayed_label is not None:
            counts["labels.delayed"] += 1
            samples.setdefault("labels.delayed", batch.delayed_label.to_dict())
        if batch.transaction.is_scripted_fraud:
            fraud_scripts[batch.transaction.fraud_script_type] = fraud_scripts.get(batch.transaction.fraud_script_type, 0) + 1

    result = {
        "event_count": event_count,
        "topic_counts": counts,
        "fraud_script_counts": dict(sorted(fraud_scripts.items())),
        "samples": samples,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("validate-schemas")
def validate_schemas(sample_count: int = 200, seed: int = 42) -> None:
    """Validate generated realtime samples against local JSON Schema files."""
    repo_root = Path(__file__).resolve().parents[3]
    schema_names = {
        "transactions.raw": "transaction-event.schema.json",
        "accounts.raw": "account-profile.schema.json",
        "devices.raw": "device-login.schema.json",
        "blacklist.raw": "blacklist-event.schema.json",
        "labels.delayed": "delayed-label.schema.json",
    }
    schemas = {topic: load_schema(repo_root, name) for topic, name in schema_names.items()}
    simulator = MultiSourceFraudSimulator(SimulatorConfig(seed=seed))
    validated_counts = {topic: 0 for topic in schema_names}
    for batch in simulator.multi_source_stream(sample_count):
        samples = {
            "transactions.raw": batch.transaction.to_dict(),
            "accounts.raw": batch.account.to_dict(),
            "devices.raw": batch.device.to_dict(),
        }
        if batch.blacklist is not None:
            samples["blacklist.raw"] = batch.blacklist.to_dict()
        if batch.delayed_label is not None:
            samples["labels.delayed"] = batch.delayed_label.to_dict()
        for topic, payload in samples.items():
            validate_json_schema_sample(schemas[topic], payload, label=topic)
            validated_counts[topic] += 1

    typer.echo(json.dumps({"sample_count": sample_count, "validated_counts": validated_counts}, ensure_ascii=False, indent=2))


@app.command("topics")
def topics() -> None:
    """Print the Kafka topics used by the full realtime platform."""
    names = [
        "transactions.raw",
        "transactions.cleaned",
        "features.realtime",
        "risk.scored",
        "risk.alerts",
        "risk.audit",
        "devices.raw",
        "accounts.raw",
        "blacklist.raw",
        "labels.delayed",
    ]
    typer.echo("\n".join(names))


@app.command("submit-flink")
def submit_flink() -> None:
    """Submit the PyFlink realtime feature job through Docker Compose."""
    repo_root = Path(__file__).resolve().parents[3]
    compose_file = repo_root / "infra" / "realtime" / "docker-compose.yml"
    docker = shutil.which("docker") or shutil.which("docker.exe")
    if docker is None:
        raise typer.BadParameter("找不到 docker 命令。请在安装 Docker 的环境中执行，例如 WSL。")
    subprocess.run(
        [
            docker,
            "compose",
            "-f",
            str(compose_file),
            "--profile",
            "flink-job",
            "up",
            "flink-submit-realtime-features",
        ],
        cwd=repo_root,
        check=True,
    )


@app.command("produce")
def produce(
    event_count: int = 10_000,
    interval_ms: int = 100,
    seed: int = 42,
    event_id_start: int = 0,
    timestamp_start: int = 0,
    bootstrap_servers: str = typer.Option("", help="Kafka bootstrap servers."),
) -> None:
    """Produce simulated multi-source transactions into Kafka."""
    produce_simulated_transactions(
        bootstrap_servers=bootstrap_servers or os.getenv("DG_BOOTSTRAP_SERVERS", "localhost:9094"),
        topic="transactions.raw",
        event_count=event_count,
        interval_ms=interval_ms,
        seed=seed,
        event_id_start=event_id_start,
        timestamp_start=timestamp_start,
    )


@app.command("e2e-check")
def e2e_check(
    event_count: int = 1_000,
    interval_ms: int = 0,
    seed: int = 42,
    timeout_sec: int = 90,
    bootstrap_servers: str = typer.Option("", help="Kafka bootstrap servers."),
    database_url: str = typer.Option("", help="PostgreSQL connection URL."),
    redis_url: str = typer.Option("", help="Redis connection URL."),
    neo4j_uri: str = typer.Option("", help="Neo4j bolt URI."),
    neo4j_user: str = typer.Option("neo4j", help="Neo4j user."),
    neo4j_password: str = typer.Option("dgcheater", help="Neo4j password."),
    api_url: str = typer.Option("http://127.0.0.1:8060", help="Realtime dashboard API URL."),
    output_path: Path | None = None,
) -> None:
    """Verify the running realtime platform from Kafka production to dashboard snapshot."""
    result = run_e2e_check(
        event_count=event_count,
        interval_ms=interval_ms,
        seed=seed,
        timeout_sec=timeout_sec,
        bootstrap_servers=bootstrap_servers or os.getenv("DG_BOOTSTRAP_SERVERS", "localhost:9094"),
        database_url=database_url or os.getenv("DG_DATABASE_URL", "postgresql://dgcheater:dgcheater@localhost:55432/dgcheater"),
        redis_url=redis_url or os.getenv("DG_REDIS_URL", "redis://localhost:6379/0"),
        neo4j_uri=neo4j_uri or os.getenv("DG_NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=neo4j_user or os.getenv("DG_NEO4J_USER", "neo4j"),
        neo4j_password=neo4j_password or os.getenv("DG_NEO4J_PASSWORD", "dgcheater"),
        api_url=api_url,
    )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("feature-worker")
def feature_worker(
    bootstrap_servers: str = typer.Option("", help="Kafka bootstrap servers."),
    group_id: str = "dgcheater-feature-worker",
    auto_offset_reset: str = typer.Option("latest", help="Kafka offset policy: latest or earliest."),
) -> None:
    """Consume raw multi-source events and publish realtime features."""
    run_multisource_feature_worker(
        bootstrap_servers=bootstrap_servers or os.getenv("DG_BOOTSTRAP_SERVERS", "localhost:9094"),
        transaction_topic="transactions.raw",
        account_topic="accounts.raw",
        device_topic="devices.raw",
        blacklist_topic="blacklist.raw",
        output_topic="features.realtime",
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
    )


@app.command("scoring-worker")
def scoring_worker(
    bootstrap_servers: str = typer.Option("", help="Kafka bootstrap servers."),
    database_url: str = typer.Option("", help="PostgreSQL connection URL."),
    redis_url: str = typer.Option("", help="Redis connection URL."),
    neo4j_uri: str = typer.Option("", help="Neo4j bolt URI."),
    neo4j_user: str = typer.Option("neo4j", help="Neo4j user."),
    neo4j_password: str = typer.Option("dgcheater", help="Neo4j password."),
    group_id: str = "dgcheater-scoring-worker",
    auto_offset_reset: str = typer.Option("latest", help="Kafka offset policy: latest or earliest."),
) -> None:
    """Consume realtime features, score risk and persist high-risk alerts."""
    run_scoring_worker(
        bootstrap_servers=bootstrap_servers or os.getenv("DG_BOOTSTRAP_SERVERS", "localhost:9094"),
        input_topic="features.realtime",
        scored_topic="risk.scored",
        alerts_topic="risk.alerts",
        audit_topic="risk.audit",
        group_id=group_id,
        database_url=database_url or os.getenv("DG_DATABASE_URL", "postgresql://dgcheater:dgcheater@localhost:55432/dgcheater"),
        redis_url=redis_url or os.getenv("DG_REDIS_URL", ""),
        neo4j_uri=neo4j_uri or os.getenv("DG_NEO4J_URI", ""),
        neo4j_user=neo4j_user or os.getenv("DG_NEO4J_USER", "neo4j"),
        neo4j_password=neo4j_password or os.getenv("DG_NEO4J_PASSWORD", "dgcheater"),
        auto_offset_reset=auto_offset_reset,
    )


if __name__ == "__main__":
    app()
