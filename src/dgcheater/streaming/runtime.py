from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import time
from typing import Any

import pandas as pd
from pydantic import BaseModel
import requests
import typer

from ..core.config import APP_CONFIG
from ..dashboard.graph_stream_assets import GRAPH_STREAM_HTML
from ..dashboard.builder import build_showcase_dashboard
from ..datasets.registry import get_dataset_spec
from ..datasets.loaders import TabularDataset, load_dataset_from_spec
from .dynamic_graph import DynamicGraphConfig, DynamicGraphDetector
from .event_store import RiskEventStore, events_from_csv_and_trace, events_from_jsonl, resolve_database_url
from .prototype import OnlineRiskScorer, build_transaction_stream


app = typer.Typer(no_args_is_help=True)


class ScoreRequest(BaseModel):
    events: list[dict[str, Any]]


@dataclass(slots=True)
class RuntimeConfig:
    dataset: str
    data_path: Path
    output_dir: Path
    kafka_bootstrap_servers: str
    input_topic: str
    output_topic: str
    scorer_url: str
    batch_size: int
    event_count: int
    replay_interval_ms: int
    result_output_path: Path
    consume_max_messages: int
    consume_timeout_seconds: int
    score_http_event_count: int
    database_url: str

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        settings = APP_CONFIG.streaming.runtime
        dataset = os.getenv("DGC_DATASET", settings.dataset)
        spec = get_dataset_spec(dataset)
        default_data_path = settings.data_path if dataset == settings.dataset else spec.default_path
        if default_data_path is None:
            default_data_path = APP_CONFIG.paths.data_root / dataset
        return cls(
            dataset=dataset,
            data_path=Path(os.getenv("DGC_DATA_PATH", str(default_data_path))),
            output_dir=Path(os.getenv("DGC_OUTPUT_DIR", str(settings.output_dir))),
            kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", settings.kafka_bootstrap_servers),
            input_topic=os.getenv("DGC_INPUT_TOPIC", settings.input_topic),
            output_topic=os.getenv("DGC_OUTPUT_TOPIC", settings.output_topic),
            scorer_url=os.getenv("DGC_SCORER_URL", settings.scorer_url),
            batch_size=int(os.getenv("DGC_BATCH_SIZE", str(settings.batch_size))),
            event_count=int(os.getenv("DGC_EVENT_COUNT", str(settings.event_count))),
            replay_interval_ms=int(os.getenv("DGC_REPLAY_INTERVAL_MS", str(settings.replay_interval_ms))),
            result_output_path=Path(os.getenv("DGC_RESULT_OUTPUT_PATH", str(settings.result_output_path))),
            consume_max_messages=int(os.getenv("DGC_CONSUME_MAX_MESSAGES", str(settings.consume_max_messages))),
            consume_timeout_seconds=int(os.getenv("DGC_CONSUME_TIMEOUT_SECONDS", str(settings.consume_timeout_seconds))),
            score_http_event_count=int(os.getenv("DGC_SCORE_HTTP_EVENT_COUNT", str(settings.score_http_event_count))),
            database_url=resolve_database_url(
                os.getenv("DGC_DATABASE_URL", settings.database_url),
                Path(os.getenv("DGC_OUTPUT_DIR", str(settings.output_dir))),
            ),
        )


def load_graph_dataset(config: RuntimeConfig):
    spec = get_dataset_spec(config.dataset)
    raw = load_dataset_from_spec(spec, config.data_path)
    if isinstance(raw, TabularDataset):
        raise RuntimeError("Streaming runtime requires a graph dataset.")
    return raw


def make_scorer(config: RuntimeConfig) -> OnlineRiskScorer:
    raw = load_graph_dataset(config)
    return OnlineRiskScorer(raw, dataset_key=config.dataset, output_dir=config.output_dir)


def normalize_event_batch(events: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(events)
    required_columns = {
        "event_id",
        "timestamp",
        "src_node",
        "dst_node",
        "edge_type",
        "channel",
        "amount",
        "device_fingerprint",
    }
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise ValueError(f"Missing event columns: {missing}")
    if "is_fraud_edge" not in frame.columns:
        frame["is_fraud_edge"] = -1
    return frame


@app.command("serve-scorer")
def serve_scorer(
    host: str = typer.Option(APP_CONFIG.streaming.runtime.host),
    port: int = typer.Option(APP_CONFIG.streaming.runtime.port),
) -> None:
    """Start the FastAPI risk scoring service."""
    import uvicorn
    from fastapi import FastAPI

    config = RuntimeConfig.from_env()
    scorer = make_scorer(config)
    api = FastAPI(title="DGCheater Risk Scorer", version="0.1.0")

    @api.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "dataset": config.dataset,
            "batch_size": config.batch_size,
        }

    @api.post("/score-batch")
    def score_batch(request: ScoreRequest) -> dict[str, object]:
        frame = normalize_event_batch(request.events)
        risk_frame, metrics = scorer.score_frame(frame)
        return {
            "metrics": metrics,
            "results": risk_frame.to_dict(orient="records"),
        }

    uvicorn.run(api, host=host, port=port)


@app.command("produce")
def produce() -> None:
    """Generate replay events and publish them to Kafka."""
    from confluent_kafka import Producer

    config = RuntimeConfig.from_env()
    raw = load_graph_dataset(config)
    stream_frame = build_transaction_stream(raw, event_count=config.event_count)
    producer = Producer({"bootstrap.servers": config.kafka_bootstrap_servers})

    delivered = 0

    def delivery_callback(err, msg) -> None:
        nonlocal delivered
        if err is not None:
            raise RuntimeError(f"Kafka delivery failed: {err}")
        delivered += 1

    for row in stream_frame.to_dict(orient="records"):
        producer.produce(
            config.input_topic,
            key=str(row["event_id"]),
            value=json.dumps(row, ensure_ascii=False),
            callback=delivery_callback,
        )
        producer.poll(0)
        if config.replay_interval_ms > 0:
            time.sleep(config.replay_interval_ms / 1_000)
    producer.flush()
    typer.echo(f"Published {delivered} events to {config.input_topic}")


@app.command("consume-results")
def consume_results(
    output_path: Path = typer.Option(APP_CONFIG.streaming.runtime.result_output_path),
    max_messages: int = typer.Option(APP_CONFIG.streaming.runtime.consume_max_messages),
    timeout_seconds: int = typer.Option(APP_CONFIG.streaming.runtime.consume_timeout_seconds),
    write_store: bool = typer.Option(True),
) -> None:
    """Consume risk events from Kafka into jsonl and the event store."""
    from confluent_kafka import Consumer

    config = RuntimeConfig.from_env()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    store = RiskEventStore(config.database_url) if write_store else None
    if store is not None:
        store.init_schema()
    consumer = Consumer(
        {
            "bootstrap.servers": config.kafka_bootstrap_servers,
            "group.id": "dgcheater-result-consumer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe([config.output_topic])
    deadline = time.time() + timeout_seconds
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        while count < max_messages and time.time() < deadline:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                raise RuntimeError(str(message.error()))
            line = message.value().decode("utf-8")
            handle.write(line + "\n")
            if store is not None:
                store.upsert_events([json.loads(line)])
            count += 1
    consumer.close()
    store_note = f" and {config.database_url}" if store is not None else ""
    typer.echo(f"Consumed {count} messages from {config.output_topic} into {output_path}{store_note}")


@app.command("init-store")
def init_store() -> None:
    """Initialize the local risk event store."""
    config = RuntimeConfig.from_env()
    store = RiskEventStore(config.database_url)
    store.init_schema()
    typer.echo(f"Initialized event store at {config.database_url}")


@app.command("import-risk-events")
def import_risk_events(
    risk_path: Path = typer.Option(Path("output/streaming/risk_events.csv")),
    trace_path: Path = typer.Option(Path("output/streaming/ring_trace_summary.json")),
) -> None:
    """Import generated risk event files into the event store."""
    config = RuntimeConfig.from_env()
    store = RiskEventStore(config.database_url)
    count = store.upsert_events(events_from_csv_and_trace(risk_path, trace_path))
    typer.echo(f"Imported {count} risk events into {config.database_url}")


@app.command("import-jsonl")
def import_jsonl(
    jsonl_path: Path = typer.Option(APP_CONFIG.streaming.runtime.result_output_path),
) -> None:
    """Import Kafka result jsonl into the event store."""
    config = RuntimeConfig.from_env()
    store = RiskEventStore(config.database_url)
    count = store.upsert_events(events_from_jsonl(jsonl_path))
    typer.echo(f"Imported {count} risk events into {config.database_url}")


@app.command("serve-dashboard")
def serve_dashboard(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8050),
    dashboard_path: Path = typer.Option(APP_CONFIG.dashboard.output_path),
) -> None:
    """Serve the showcase dashboard with a live risk-event API."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import FileResponse

    config = RuntimeConfig.from_env()
    build_showcase_dashboard(output_path=dashboard_path, output_dir=config.output_dir)
    store = RiskEventStore(config.database_url)
    store.init_schema()
    api = FastAPI(title="DGCheater Live Dashboard", version="0.1.0")

    @api.get("/")
    def index() -> FileResponse:
        return FileResponse(dashboard_path)

    @api.get("/api/risk-events")
    def risk_events(limit: int = 12) -> dict[str, object]:
        summary = store.summary()
        return {
            "available": True,
            "summary": {
                "caseCount": summary.event_count,
                "criticalCount": summary.critical_count,
                "highCount": summary.high_count,
                "mediumCount": summary.medium_count,
                "lowCount": summary.low_count,
                "auditCount": min(summary.event_count, limit),
            },
            "cases": store.load_cases(limit=limit),
        }

    @api.get("/health")
    def health() -> dict[str, object]:
        summary = store.summary()
        return {
            "status": "ok",
            "database": config.database_url,
            "riskEventCount": summary.event_count,
        }

    uvicorn.run(api, host=host, port=port)


@app.command("serve-graph-stream")
def serve_graph_stream(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8060),
    event_count: int = typer.Option(5_000, min=100, max=100_000),
    window_size: int = typer.Option(900, min=50, max=2_000),
    replay_interval_ms: int = typer.Option(180, min=20, max=5_000),
) -> None:
    """Serve a timestamp-ordered dynamic DGraph-Fin transaction graph."""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles

    config = RuntimeConfig.from_env()
    raw = load_graph_dataset(config)
    detector = DynamicGraphDetector(
        raw,
        dataset_key=config.dataset,
        output_dir=config.output_dir,
        config=DynamicGraphConfig(
            event_count=event_count,
            window_size=window_size,
            replay_interval_ms=replay_interval_ms,
        ),
    )
    api = FastAPI(title="DGCheater Dynamic Graph Stream", version="0.1.0")
    frontend_dist = Path("frontend/graph-stream/dist")
    frontend_index = frontend_dist / "index.html"
    if (frontend_dist / "assets").exists():
        api.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="graph-stream-assets")

    @api.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse | FileResponse:
        if frontend_index.exists():
            return FileResponse(frontend_index)
        return GRAPH_STREAM_HTML

    @api.get("/api/graph-stream")
    def graph_stream() -> dict[str, object]:
        return detector.snapshot()

    @api.post("/api/graph-stream/reset")
    def reset_graph_stream() -> dict[str, object]:
        return detector.reset()

    @api.get("/api/graph-node-neighborhood")
    def graph_node_neighborhood(
        node_id: int,
        scope: str = "full",
        limit: int = 80,
    ) -> dict[str, object]:
        safe_scope = scope if scope in {"full", "window"} else "full"
        safe_limit = max(1, min(limit, 260))
        return detector.node_neighborhood(node_id=node_id, scope=safe_scope, limit=safe_limit)

    @api.get("/health")
    def health() -> dict[str, object]:
        snapshot = detector.snapshot()
        return {
            "status": "ok",
            "dataset": config.dataset,
            "position": snapshot["meta"]["position"],
            "totalEvents": snapshot["meta"]["totalEvents"],
        }

    uvicorn.run(api, host=host, port=port)


@app.command("score-http-once")
def score_http_once(
    event_count: int = typer.Option(APP_CONFIG.streaming.runtime.score_http_event_count),
) -> None:
    """Smoke-test the scorer HTTP endpoint without Kafka."""
    config = RuntimeConfig.from_env()
    raw = load_graph_dataset(config)
    stream_frame = build_transaction_stream(raw, event_count=event_count)
    response = requests.post(
        config.scorer_url,
        json={"events": stream_frame.to_dict(orient="records")},
        timeout=60,
    )
    response.raise_for_status()
    typer.echo(json.dumps(response.json()["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app()
