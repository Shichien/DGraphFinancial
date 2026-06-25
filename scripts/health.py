from __future__ import annotations

from dataclasses import dataclass
import argparse
import sys

import requests

from dgcheater.config import APP_CONFIG


@dataclass(frozen=True)
class Endpoint:
    name: str
    url: str


@dataclass(frozen=True)
class HealthResult:
    endpoint: Endpoint
    ok: bool
    detail: str


ENDPOINTS = tuple(
    Endpoint(endpoint.name, endpoint.url)
    for endpoint in APP_CONFIG.streaming.health_endpoints
)


def check_endpoint(endpoint: Endpoint, timeout_seconds: float) -> HealthResult:
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(endpoint.url, timeout=timeout_seconds)
    except requests.RequestException as exc:
        return HealthResult(endpoint=endpoint, ok=False, detail=str(exc))

    if response.status_code != 200:
        return HealthResult(
            endpoint=endpoint,
            ok=False,
            detail=f"HTTP {response.status_code}: {response.text[:200]}",
        )
    return HealthResult(endpoint=endpoint, ok=True, detail="ok")


def check_all(timeout_seconds: float = 5.0) -> list[HealthResult]:
    return [check_endpoint(endpoint, timeout_seconds) for endpoint in ENDPOINTS]


def print_results(results: list[HealthResult]) -> None:
    for result in results:
        state = "ok" if result.ok else "fail"
        print(f"{state:4} {result.endpoint.name}: {result.detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check streaming service health endpoints.")
    parser.add_argument("--timeout", type=float, default=APP_CONFIG.streaming.health_request_timeout_seconds, help="HTTP timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = check_all(timeout_seconds=args.timeout)
    print_results(results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
