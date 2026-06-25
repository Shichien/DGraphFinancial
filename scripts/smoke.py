from __future__ import annotations

import argparse
import sys

from dgcheater.config import APP_CONFIG

from consume import DEFAULT_OUTPUT_PATH, consume_results, summarize_output
from runtime import run_compose
from wait import wait_for_services


def start_streaming_stack() -> None:
    run_compose(["up", "-d"])


def produce_events(event_count: int) -> None:
    run_compose(
        [
            "--profile",
            "tools",
            "run",
            "--rm",
            "-e",
            f"DGC_EVENT_COUNT={event_count}",
            "producer",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the streaming Docker Compose smoke flow.")
    parser.add_argument("--event-count", type=int, default=APP_CONFIG.streaming.prototype.event_count)
    parser.add_argument("--wait-timeout-seconds", type=float, default=APP_CONFIG.streaming.wait_timeout_seconds)
    parser.add_argument("--consume-timeout-seconds", type=int, default=APP_CONFIG.streaming.runtime.consume_timeout_seconds)
    parser.add_argument("--lines", type=int, default=APP_CONFIG.streaming.smoke_result_lines)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start_streaming_stack()
    wait_for_services(timeout_seconds=args.wait_timeout_seconds)
    produce_events(event_count=args.event_count)
    output_path = consume_results(
        max_messages=args.event_count,
        timeout_seconds=args.consume_timeout_seconds,
        output_path=DEFAULT_OUTPUT_PATH,
    )
    summarize_output(output_path, lines=args.lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
