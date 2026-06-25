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
from ..datasets.registry import get_dataset_spec
from ..datasets.loaders import TabularDataset, load_dataset_from_spec
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
) -> None:
    """Consume risk events from Kafka into a jsonl file."""
    from confluent_kafka import Consumer

    config = RuntimeConfig.from_env()
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
            handle.write(message.value().decode("utf-8") + "\n")
            count += 1
    consumer.close()
    typer.echo(f"Consumed {count} messages from {config.output_topic} into {output_path}")


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
