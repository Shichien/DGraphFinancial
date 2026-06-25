from __future__ import annotations

import argparse
import sys

from runtime import run_compose


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run streaming Docker Compose commands from project config.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("up")
    subparsers.add_parser("down")
    subparsers.add_parser("stop")

    logs_parser = subparsers.add_parser("logs")
    logs_parser.add_argument("service", nargs="?")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "up":
        run_compose(["up", "-d"])
        return 0
    if args.command == "down":
        run_compose(["down"])
        return 0
    if args.command == "stop":
        run_compose(["stop"])
        return 0
    if args.command == "logs":
        compose_args = ["logs", "-f"]
        if args.service:
            compose_args.append(args.service)
        run_compose(compose_args)
        return 0
    raise ValueError(args.command)


if __name__ == "__main__":
    sys.exit(main())
