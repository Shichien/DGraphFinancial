from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaValidationError(ValueError):
    pass


def load_schema(repo_root: Path, name: str) -> dict[str, Any]:
    path = repo_root / "packages" / "schema" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaValidationError(f"Schema 文件不是 JSON 对象：{path}")
    return data


def validate_json_schema_sample(schema: dict[str, Any], payload: dict[str, Any], *, label: str) -> None:
    required = schema.get("required", [])
    if not isinstance(required, list):
        raise SchemaValidationError(f"{label}: required 必须是数组")
    for key in required:
        if key not in payload:
            raise SchemaValidationError(f"{label}: 缺少字段 {key}")

    if schema.get("additionalProperties") is False:
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise SchemaValidationError(f"{label}: properties 必须是对象")
        extra_keys = sorted(set(payload) - set(properties))
        if extra_keys:
            raise SchemaValidationError(f"{label}: 存在未声明字段 {extra_keys}")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise SchemaValidationError(f"{label}: properties 必须是对象")
    for key, value in payload.items():
        rule = properties.get(key)
        if not isinstance(rule, dict):
            continue
        _validate_field(rule, value, label=f"{label}.{key}")


def _validate_field(rule: dict[str, Any], value: Any, *, label: str) -> None:
    if "enum" in rule:
        allowed = rule["enum"]
        if value not in allowed:
            raise SchemaValidationError(f"{label}: 值 {value!r} 不在枚举 {allowed!r} 中")

    expected_type = rule.get("type")
    if expected_type is not None and not _matches_type(value, str(expected_type)):
        raise SchemaValidationError(f"{label}: 类型不匹配，期望 {expected_type}，实际 {type(value).__name__}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = rule.get("minimum")
        maximum = rule.get("maximum")
        if minimum is not None and value < float(minimum):
            raise SchemaValidationError(f"{label}: 值 {value} 小于最小值 {minimum}")
        if maximum is not None and value > float(maximum):
            raise SchemaValidationError(f"{label}: 值 {value} 大于最大值 {maximum}")

    if rule.get("type") == "array":
        item_rule = rule.get("items")
        if isinstance(item_rule, dict):
            for index, item in enumerate(value):
                _validate_field(item_rule, item, label=f"{label}[{index}]")


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return True
