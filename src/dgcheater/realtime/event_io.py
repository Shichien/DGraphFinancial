from __future__ import annotations

import json
from dataclasses import is_dataclass
from typing import Any


def to_json_bytes(payload: Any) -> bytes:
    if is_dataclass(payload):
        payload = payload.to_dict()
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def from_json_bytes(payload: bytes | str) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Kafka payload must be a JSON object.")
    return data
