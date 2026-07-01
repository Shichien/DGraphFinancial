from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


SUBJECTS = {
    "transactions.raw-value": "transaction-event.schema.json",
    "accounts.raw-value": "account-profile.schema.json",
    "devices.raw-value": "device-login.schema.json",
    "blacklist.raw-value": "blacklist-event.schema.json",
    "labels.delayed-value": "delayed-label.schema.json",
    "features.realtime-value": "realtime-features.schema.json",
    "risk.scored-value": "risk-decision.schema.json",
    "risk.alerts-value": "risk-decision.schema.json",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-url", required=True)
    parser.add_argument("--schema-dir", type=Path, required=True)
    args = parser.parse_args()
    registry_url = str(args.registry_url).rstrip("/")
    wait_until_ready(registry_url)
    for subject, schema_name in SUBJECTS.items():
        schema_path = args.schema_dir / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        register_schema(registry_url, subject, _schema_registry_compatible(schema))
        print(f"registered {subject} from {schema_name}")
    return 0


def wait_until_ready(registry_url: str) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{registry_url}/subjects", timeout=5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)
    raise TimeoutError("Schema Registry not ready")


def register_schema(registry_url: str, subject: str, schema: dict[str, object]) -> None:
    payload = json.dumps(
        {
            "schemaType": "JSON",
            "schema": json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{registry_url}/subjects/{subject}/versions",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status not in {200, 201}:
                raise RuntimeError(f"failed to register {subject}: {response.status}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"failed to register {subject}: HTTP {error.code}: {detail}") from error


def _schema_registry_compatible(schema: dict[str, object]) -> dict[str, object]:
    converted = dict(schema)
    converted["$schema"] = "http://json-schema.org/draft-07/schema#"
    return converted


if __name__ == "__main__":
    raise SystemExit(main())
