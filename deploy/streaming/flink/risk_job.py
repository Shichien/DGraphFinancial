from __future__ import annotations

import json
import os
import time
from typing import Iterable

import requests

from pyflink.common import SimpleStringSchema, WatermarkStrategy
from pyflink.common.serialization import Encoder
from pyflink.common.typeinfo import Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.file_system import FileSink, OutputFileConfig, RollingPolicy
from pyflink.datastream.connectors.kafka import KafkaOffsetsInitializer, KafkaRecordSerializationSchema, KafkaSink, KafkaSource
from pyflink.datastream.functions import FlatMapFunction, RuntimeContext


class ScoreBatchFunction(FlatMapFunction):
    def __init__(self, scorer_url: str, batch_size: int) -> None:
        self.scorer_url = scorer_url
        self.batch_size = batch_size
        self.buffer: list[dict[str, object]] = []

    def open(self, runtime_context: RuntimeContext) -> None:
        self.session = requests.Session()

    def flat_map(self, value: str) -> Iterable[str]:
        self.buffer.append(json.loads(value))
        if len(self.buffer) < self.batch_size:
            return []
        return self._flush()

    def close(self) -> None:
        if self.buffer:
            self._flush()

    def _flush(self) -> list[str]:
        batch = self.buffer
        self.buffer = []
        response = self.session.post(self.scorer_url, json={"events": batch}, timeout=60)
        response.raise_for_status()
        payload = response.json()
        emitted_at = int(time.time() * 1000)
        return [
            json.dumps({"emitted_at": emitted_at, **item}, ensure_ascii=False)
            for item in payload["results"]
        ]


def main() -> None:
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    input_topic = os.getenv("DGC_INPUT_TOPIC", "transactions.raw")
    output_topic = os.getenv("DGC_OUTPUT_TOPIC", "transactions.risk")
    scorer_url = os.getenv("DGC_SCORER_URL", "http://risk-scorer:8000/score-batch")
    batch_size = int(os.getenv("DGC_BATCH_SIZE", "256"))

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_topics(input_topic)
        .set_group_id("dgcheater-flink-risk-job")
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )
    sink = (
        KafkaSink.builder()
        .set_bootstrap_servers(bootstrap_servers)
        .set_record_serializer(
            KafkaRecordSerializationSchema.builder()
            .set_topic(output_topic)
            .set_value_serialization_schema(SimpleStringSchema())
            .build()
        )
        .build()
    )

    stream = env.from_source(
        source,
        watermark_strategy=WatermarkStrategy.no_watermarks(),
        source_name="transactions-raw",
    )
    risk_stream = stream.flat_map(
        ScoreBatchFunction(scorer_url=scorer_url, batch_size=batch_size),
        output_type=Types.STRING(),
    )
    risk_stream.sink_to(sink)

    # Also write a local trace inside the Flink container for quick debugging.
    file_sink = (
        FileSink.for_row_format("/tmp/dgcheater-risk-events", Encoder.simple_string_encoder())
        .with_output_file_config(OutputFileConfig.builder().with_part_prefix("risk").with_part_suffix(".jsonl").build())
        .with_rolling_policy(RollingPolicy.default_rolling_policy())
        .build()
    )
    risk_stream.sink_to(file_sink)
    env.execute("DGCheater Kafka-Flink Risk Scoring")


if __name__ == "__main__":
    main()
