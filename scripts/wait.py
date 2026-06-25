from __future__ import annotations

import argparse
import sys
import time

from dgcheater.config import APP_CONFIG

from health import HealthResult, check_all, print_results


def wait_for_services(
    timeout_seconds: float = APP_CONFIG.streaming.wait_timeout_seconds,
    interval_seconds: float = APP_CONFIG.streaming.wait_interval_seconds,
    request_timeout_seconds: float = APP_CONFIG.streaming.health_request_timeout_seconds,
) -> list[HealthResult]:
    deadline = time.monotonic() + timeout_seconds
    last_results: list[HealthResult] = []

    while time.monotonic() <= deadline:
        last_results = check_all(timeout_seconds=request_timeout_seconds)
        if all(result.ok for result in last_results):
            return last_results
        time.sleep(interval_seconds)

    raise TimeoutError("streaming services did not become ready")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wait until streaming services become healthy.")
    parser.add_argument("--timeout-seconds", type=float, default=APP_CONFIG.streaming.wait_timeout_seconds)
    parser.add_argument("--interval-seconds", type=float, default=APP_CONFIG.streaming.wait_interval_seconds)
    parser.add_argument("--request-timeout-seconds", type=float, default=APP_CONFIG.streaming.health_request_timeout_seconds)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = wait_for_services(
            timeout_seconds=args.timeout_seconds,
            interval_seconds=args.interval_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
        )
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        print_results(check_all(timeout_seconds=args.request_timeout_seconds))
        return 1

    print_results(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
