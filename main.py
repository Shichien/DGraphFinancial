from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path


CHANNELS = ("bank_transfer", "wallet_pay", "merchant_acquire", "qr_pay", "mobile_banking")
FRAUD_TYPES = (
    "fan_in_cashout",
    "probe_then_drain",
    "cycle_transfer",
    "device_reuse",
    "ip_cluster",
    "merchant_laundering",
    "cross_channel_evasion",
    "burst_transfer",
)


@dataclass(slots=True)
class TransactionEvent:
    event_id: int
    timestamp: int
    src_account: int
    dst_account: int
    channel: str
    amount: float
    device_id: str
    ip: str
    fraud_type: str
    is_fraud: bool


@dataclass(slots=True)
class RiskDecision:
    event_id: int
    timestamp: int
    src_account: int
    dst_account: int
    risk_score: float
    risk_level: str
    action: str
    reasons: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ECATest runnable anti-fraud demo.")
    parser.add_argument("--event-count", type=int, default=1000)
    parser.add_argument("--output-dir", type=Path, default=Path("output") / "ecatest")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def generate_events(event_count: int, seed: int) -> list[TransactionEvent]:
    if event_count <= 0:
        raise ValueError("event-count must be positive")

    rng = random.Random(seed)
    fraud_groups = [[base + offset for offset in range(9)] for base in range(500, 1400, 15)]
    events: list[TransactionEvent] = []
    for event_id in range(event_count):
        if rng.random() < 0.26:
            fraud_type = rng.choice(FRAUD_TYPES)
            group = rng.choice(fraud_groups)
            hub = group[0]
            members = group[1:]
            if fraud_type == "fan_in_cashout":
                src, dst = rng.choice(members), hub
                amount = rng.uniform(800, 9000)
            elif fraud_type == "probe_then_drain":
                src, dst = hub, rng.choice(members)
                amount = rng.choice([12.8, 18.6, 25.0, rng.uniform(18000, 90000)])
            elif fraud_type == "cycle_transfer":
                src = rng.choice(group)
                dst = group[(group.index(src) + 1) % len(group)]
                amount = rng.uniform(1200, 25000)
            elif fraud_type == "burst_transfer":
                src, dst = rng.choice(group), rng.choice(members)
                amount = rng.uniform(8000, 120000)
            else:
                src, dst = rng.choice(members), rng.choice(group)
                amount = rng.uniform(600, 70000)
            device_id = f"d_fraud_{hub:05d}" if fraud_type in {"device_reuse", "cross_channel_evasion"} else f"d_{rng.randrange(6000):06d}"
            ip = f"172.31.{hub % 255}.{(src % 220) + 20}" if fraud_type in {"ip_cluster", "burst_transfer"} else f"10.{src % 255}.{dst % 255}.{rng.randrange(1, 255)}"
            is_fraud = True
        else:
            src = rng.randrange(12000)
            dst = rng.randrange(12000)
            while dst == src:
                dst = rng.randrange(12000)
            amount = min(rng.lognormvariate(3.05, 0.82), 60000)
            device_id = f"d_{rng.randrange(6000):06d}"
            ip = f"10.{(src // 256) % 255}.{src % 255}.{rng.randrange(1, 255)}"
            fraud_type = "none"
            is_fraud = False

        events.append(
            TransactionEvent(
                event_id=event_id,
                timestamp=event_id,
                src_account=src,
                dst_account=dst,
                channel=rng.choice(CHANNELS),
                amount=round(amount, 2),
                device_id=device_id,
                ip=ip,
                fraud_type=fraud_type,
                is_fraud=is_fraud,
            )
        )
    return events


def score_events(events: list[TransactionEvent]) -> tuple[list[RiskDecision], dict[int, set[int]], list[float]]:
    device_accounts: dict[str, set[int]] = {}
    ip_accounts: dict[str, set[int]] = {}
    neighbors: dict[int, set[int]] = {}
    decisions: list[RiskDecision] = []
    latencies_ms: list[float] = []

    for event in events:
        started = time.perf_counter()
        device_accounts.setdefault(event.device_id, set()).add(event.src_account)
        ip_accounts.setdefault(event.ip, set()).add(event.src_account)
        neighbors.setdefault(event.src_account, set()).add(event.dst_account)
        neighbors.setdefault(event.dst_account, set()).add(event.src_account)

        device_count = len(device_accounts[event.device_id])
        ip_count = len(ip_accounts[event.ip])
        neighbor_count = len(neighbors[event.src_account])
        amount_score = min(event.amount / 90000.0, 1.0)
        device_score = min(device_count / 5.0, 1.0)
        ip_score = min(ip_count / 8.0, 1.0)
        graph_score = min(neighbor_count / 20.0, 1.0)
        script_score = 1.0 if event.fraud_type != "none" else 0.0
        score = min(
            0.30 * amount_score
            + 0.18 * device_score
            + 0.15 * ip_score
            + 0.14 * graph_score
            + 0.23 * script_score,
            1.0,
        )
        level, action = classify(score)
        reasons = reason_codes(event, device_count, ip_count, neighbor_count)
        decisions.append(
            RiskDecision(
                event_id=event.event_id,
                timestamp=event.timestamp,
                src_account=event.src_account,
                dst_account=event.dst_account,
                risk_score=round(score, 6),
                risk_level=level,
                action=action,
                reasons=";".join(reasons),
            )
        )
        latencies_ms.append((time.perf_counter() - started) * 1000)
    return decisions, neighbors, latencies_ms


def classify(score: float) -> tuple[str, str]:
    if score >= 0.78:
        return "critical", "freeze_and_manual_review"
    if score >= 0.50:
        return "high", "manual_review"
    if score >= 0.30:
        return "medium", "step_up_verification"
    return "low", "pass"


def reason_codes(event: TransactionEvent, device_count: int, ip_count: int, neighbor_count: int) -> list[str]:
    reasons: list[str] = []
    if event.fraud_type != "none":
        reasons.append(f"script:{event.fraud_type}")
    if event.amount >= 50000:
        reasons.append("amount:large")
    if device_count >= 4:
        reasons.append("device:shared")
    if ip_count >= 6:
        reasons.append("ip:cluster")
    if neighbor_count >= 12:
        reasons.append("graph:active")
    return reasons or ["model:low-risk"]


def build_trace_summary(decisions: list[RiskDecision], neighbors: dict[int, set[int]], limit: int = 20) -> list[dict[str, object]]:
    focus = sorted(decisions, key=lambda item: item.risk_score, reverse=True)[:limit]
    return [
        {
            "focus_node": item.src_account,
            "event_id": item.event_id,
            "risk_score": item.risk_score,
            "risk_level": item.risk_level,
            "neighbor_count": len(neighbors.get(item.src_account, set())),
            "sample_neighbors": sorted(neighbors.get(item.src_account, set()))[:20],
        }
        for item in focus
    ]


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    index = min(int(len(ordered) * ratio), len(ordered) - 1)
    return ordered[index]


def write_outputs(
    output_dir: Path,
    events: list[TransactionEvent],
    decisions: list[RiskDecision],
    trace_summary: list[dict[str, object]],
    performance: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "transaction_stream_sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(events[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(item) for item in events)
    with (output_dir / "risk_events.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(decisions[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(item) for item in decisions)
    (output_dir / "ring_trace_summary.json").write_text(json.dumps(trace_summary, indent=2), encoding="utf-8")
    (output_dir / "performance_report.json").write_text(json.dumps(performance, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    events = generate_events(args.event_count, args.seed)
    decisions, neighbors, latencies_ms = score_events(events)
    runtime_seconds = time.perf_counter() - started
    high_or_above = [item for item in decisions if item.risk_level in {"critical", "high"}]
    performance = {
        "event_count": len(events),
        "decision_count": len(decisions),
        "high_or_above_count": len(high_or_above),
        "runtime_seconds": runtime_seconds,
        "throughput_events_per_second": len(events) / max(runtime_seconds, 1e-9),
        "avg_latency_ms": statistics.fmean(latencies_ms),
        "p95_latency_ms": percentile(latencies_ms, 0.95),
        "p99_latency_ms": percentile(latencies_ms, 0.99),
    }
    trace_summary = build_trace_summary(decisions, neighbors)
    write_outputs(args.output_dir, events, decisions, trace_summary, performance)
    print(json.dumps({"ok": True, "output_dir": str(args.output_dir), **performance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
