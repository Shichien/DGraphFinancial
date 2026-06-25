from __future__ import annotations

from pathlib import Path, PurePosixPath
import argparse
import sys

from dgcheater.config import APP_CONFIG

from runtime import OUTPUT_ROOT, project_path, run_compose


DEFAULT_OUTPUT_PATH = project_path(APP_CONFIG.streaming.runtime.result_output_path)


def container_output_path(output_path: Path) -> str:
    resolved_output_path = output_path.resolve()
    output_root = OUTPUT_ROOT.resolve()
    try:
        relative_output_path = resolved_output_path.relative_to(output_root)
    except ValueError as exc:
        raise ValueError(f"output path must be under {output_root}") from exc

    return PurePosixPath("/app/output", *relative_output_path.parts).as_posix()


def consume_results(
    max_messages: int,
    timeout_seconds: int,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    output_path = project_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_compose(
        [
            "--profile",
            "tools",
            "run",
            "--rm",
            "result-consumer",
            "dgcheater-stream",
            "consume-results",
            "--output-path",
            container_output_path(output_path),
            "--max-messages",
            str(max_messages),
            "--timeout-seconds",
            str(timeout_seconds),
        ]
    )
    return output_path


def summarize_output(output_path: Path, lines: int) -> None:
    if not output_path.exists():
        raise FileNotFoundError(output_path)

    with output_path.open("r", encoding="utf-8") as handle:
        count = sum(1 for _ in handle)
    print(f"Result count: {count}")

    with output_path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index >= lines:
                break
            print(line.rstrip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume streaming risk events through Docker Compose.")
    parser.add_argument("--max-messages", type=int, default=APP_CONFIG.streaming.runtime.consume_max_messages)
    parser.add_argument("--timeout-seconds", type=int, default=APP_CONFIG.streaming.runtime.consume_timeout_seconds)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--lines", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = consume_results(
        max_messages=args.max_messages,
        timeout_seconds=args.timeout_seconds,
        output_path=args.output_path,
    )
    summarize_output(output_path, lines=args.lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
