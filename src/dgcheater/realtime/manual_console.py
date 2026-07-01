from __future__ import annotations

import cmd
import json
import shlex
from copy import deepcopy
from pathlib import Path
from typing import Any

import typer

from .feature_engine import RealtimeFeatureEngine
from .scoring import SCORE_WEIGHTS, FusionRiskScorer
from .schemas import AccountProfileEvent, BlacklistEvent, DeviceLoginEvent, RealtimeFeatures, RiskDecision, TransactionEvent


DEFAULTS: dict[str, Any] = {
    "transaction": {
        "source_channel": "wallet_pay",
        "src_account": 100,
        "dst_account": 200,
        "amount": 1200.0,
        "merchant_id": "m_manual_0001",
        "device_id": "d_manual_0001",
        "ip": "10.10.0.1",
        "geo": "CN-SH",
        "edge_type": 1,
        "scenario_id": "manual",
        "is_scripted_fraud": False,
        "fraud_script_type": "none",
    },
    "account": {
        "account_age_days": 365,
        "historical_risk_score": 0.1,
        "home_geo": "CN-SH",
        "segment": "retail",
    },
    "device": {
        "login_result": "success",
    },
    "blacklist": {
        "entity_type": "none",
        "entity_id": "",
        "risk_reason": "manual",
        "expires_in": 86400,
    },
    "batch": {
        "timestamp_step": 1,
        "shared_device": False,
        "shared_ip": False,
        "shared_merchant": False,
    },
}


ALIASES = {
    "event_id": "transaction.event_id",
    "timestamp": "transaction.timestamp",
    "channel": "transaction.source_channel",
    "src": "transaction.src_account",
    "dst": "transaction.dst_account",
    "amount": "transaction.amount",
    "merchant": "transaction.merchant_id",
    "device": "transaction.device_id",
    "ip": "transaction.ip",
    "geo": "transaction.geo",
    "edge_type": "transaction.edge_type",
    "scenario": "transaction.scenario_id",
    "scripted": "transaction.is_scripted_fraud",
    "fraud_type": "transaction.fraud_script_type",
    "historical_risk": "account.historical_risk_score",
    "risk": "account.historical_risk_score",
    "age": "account.account_age_days",
    "segment": "account.segment",
    "home_geo": "account.home_geo",
    "login": "device.login_result",
    "blacklist": "blacklist.entity_type",
    "blacklist_entity": "blacklist.entity_id",
    "blacklist_reason": "blacklist.risk_reason",
    "expires_in": "blacklist.expires_in",
    "timestamp_step": "batch.timestamp_step",
    "shared_device": "batch.shared_device",
    "shared_ip": "batch.shared_ip",
    "shared_merchant": "batch.shared_merchant",
}


class ManualRiskSession:
    def __init__(self) -> None:
        self.defaults = deepcopy(DEFAULTS)
        self.engine = RealtimeFeatureEngine()
        self.scorer = FusionRiskScorer()
        self.next_event_id = 1
        self.next_timestamp = 1
        self.results: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.defaults = deepcopy(DEFAULTS)
        self.engine = RealtimeFeatureEngine()
        self.scorer = FusionRiskScorer()
        self.next_event_id = 1
        self.next_timestamp = 1
        self.results.clear()

    def set_defaults(self, updates: dict[str, Any]) -> None:
        nested = normalize_updates(updates)
        merge_nested(self.defaults, nested)

    def score_one(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        nested = materialize(normalize_updates(payload or {}), index=0, count=1)
        transaction = self._build_transaction(nested.get("transaction", {}))
        account = self._build_account(transaction, nested.get("account", {}))
        device = self._build_device(transaction, nested.get("device", {}))
        blacklist = self._build_blacklist(transaction, nested.get("blacklist", {}))

        self.engine.ingest_account(account)
        self.engine.ingest_device(device)
        if blacklist is not None:
            self.engine.ingest_blacklist(blacklist)
        features = self.engine.transform(transaction)
        decision = self.scorer.score(features)
        result = self._result(transaction, account, device, blacklist, features, decision)
        self.results.append(result)
        return result

    def score_batch(self, count: int, spec: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if count <= 0:
            raise ValueError("count must be positive")
        normalized = normalize_updates(spec or {})
        batch_options = deepcopy(self.defaults["batch"])
        merge_nested(batch_options, normalized.get("batch", {}))
        base_event_id = self.next_event_id
        base_timestamp = self.next_timestamp
        results = []
        for index in range(count):
            item = materialize(normalized, index=index, count=count)
            transaction = item.setdefault("transaction", {})
            if "event_id" not in transaction:
                transaction["event_id"] = base_event_id + index
            if "timestamp" not in transaction:
                transaction["timestamp"] = base_timestamp + index * int(batch_options.get("timestamp_step", 1))
            if batch_options.get("shared_device") and "device_id" not in transaction:
                transaction["device_id"] = self.defaults["transaction"]["device_id"]
            if batch_options.get("shared_ip") and "ip" not in transaction:
                transaction["ip"] = self.defaults["transaction"]["ip"]
            if batch_options.get("shared_merchant") and "merchant_id" not in transaction:
                transaction["merchant_id"] = self.defaults["transaction"]["merchant_id"]
            results.append(self.score_one(item))
        return results

    def run_command(self, command: dict[str, Any]) -> list[dict[str, Any]]:
        kind = str(command.get("type", "send")).strip().lower()
        if kind == "reset":
            self.reset()
            return []
        if kind == "set":
            self.set_defaults(command.get("defaults", command.get("overrides", command)))
            return []
        if kind == "batch":
            count = int(command.get("count", 1))
            return self.score_batch(count, command)
        if kind in {"send", "event", "score"}:
            return [self.score_one(command)]
        raise ValueError(f"unknown command type: {kind}")

    def run_script(self, path: Path) -> list[dict[str, Any]]:
        commands = load_script(path)
        results: list[dict[str, Any]] = []
        for command in commands:
            results.extend(self.run_command(command))
        return results

    def _build_transaction(self, overrides: dict[str, Any]) -> TransactionEvent:
        data = deepcopy(self.defaults["transaction"])
        merge_nested(data, overrides)
        event_id = int(data.pop("event_id", self.next_event_id))
        timestamp = int(data.pop("timestamp", self.next_timestamp))
        self.next_event_id = max(self.next_event_id, event_id + 1)
        self.next_timestamp = max(self.next_timestamp, timestamp + 1)
        return TransactionEvent(
            event_id=event_id,
            timestamp=timestamp,
            source_channel=str(data["source_channel"]),
            src_account=int(data["src_account"]),
            dst_account=int(data["dst_account"]),
            amount=float(data["amount"]),
            merchant_id=str(data["merchant_id"]),
            device_id=str(data["device_id"]),
            ip=str(data["ip"]),
            geo=str(data["geo"]),
            edge_type=int(data["edge_type"]),
            scenario_id=str(data["scenario_id"]),
            is_scripted_fraud=bool(data["is_scripted_fraud"]),
            fraud_script_type=str(data["fraud_script_type"]),
        )

    def _build_account(self, transaction: TransactionEvent, overrides: dict[str, Any]) -> AccountProfileEvent:
        data = deepcopy(self.defaults["account"])
        merge_nested(data, overrides)
        return AccountProfileEvent(
            event_id=transaction.event_id,
            timestamp=transaction.timestamp,
            account_id=transaction.src_account,
            account_age_days=int(data["account_age_days"]),
            historical_risk_score=float(data["historical_risk_score"]),
            home_geo=str(data["home_geo"]),
            segment=str(data["segment"]),
            scenario_id=transaction.scenario_id,
        )

    def _build_device(self, transaction: TransactionEvent, overrides: dict[str, Any]) -> DeviceLoginEvent:
        data = deepcopy(self.defaults["device"])
        merge_nested(data, overrides)
        return DeviceLoginEvent(
            event_id=transaction.event_id,
            timestamp=transaction.timestamp,
            account_id=transaction.src_account,
            device_id=transaction.device_id,
            ip=transaction.ip,
            geo=transaction.geo,
            source_channel=transaction.source_channel,
            login_result=str(data["login_result"]),
            scenario_id=transaction.scenario_id,
        )

    def _build_blacklist(self, transaction: TransactionEvent, overrides: dict[str, Any]) -> BlacklistEvent | None:
        data = deepcopy(self.defaults["blacklist"])
        merge_nested(data, overrides)
        entity_type = str(data.get("entity_type", "none")).strip().lower()
        if entity_type in {"", "none", "false", "off", "no"}:
            return None
        entity_id = str(data.get("entity_id") or "")
        if not entity_id:
            entity_id = {
                "account": str(transaction.src_account),
                "device": transaction.device_id,
                "ip": transaction.ip,
                "merchant": transaction.merchant_id,
            }.get(entity_type, str(transaction.src_account))
        return BlacklistEvent(
            event_id=transaction.event_id,
            timestamp=transaction.timestamp,
            account_id=transaction.src_account,
            entity_type=entity_type,
            entity_id=entity_id,
            risk_reason=str(data.get("risk_reason", "manual")),
            expires_at=transaction.timestamp + int(data.get("expires_in", 86400)),
            scenario_id=transaction.scenario_id,
        )

    def _result(
        self,
        transaction: TransactionEvent,
        account: AccountProfileEvent,
        device: DeviceLoginEvent,
        blacklist: BlacklistEvent | None,
        features: RealtimeFeatures,
        decision: RiskDecision,
    ) -> dict[str, Any]:
        feature_dict = features.to_dict()
        decision_dict = decision.to_dict()
        return {
            "index": len(self.results) + 1,
            "input": {
                "transaction": transaction.to_dict(),
                "account": account.to_dict(),
                "device": device.to_dict(),
                "blacklist": blacklist.to_dict() if blacklist is not None else None,
            },
            "features": feature_dict,
            "decision": decision_dict,
            "score_breakdown": score_breakdown(decision),
            "summary": concise_summary(decision),
        }


class RiskConsole(cmd.Cmd):
    intro = (
        "DGCheater risk console. Type help for commands. "
        "Use batch 10 amount=5000..90000 shared_device=true blacklist=device to generate events."
    )
    prompt = "dg-risk> "

    def __init__(self, session: ManualRiskSession) -> None:
        super().__init__()
        self.session = session

    def do_send(self, arg: str) -> None:
        "Score one event. Example: send src=560 dst=568 amount=80000 blacklist=device login=challenge"
        try:
            result = self.session.score_one(parse_assignments(arg))
            print_result_line(result)
        except Exception as exc:
            print_error(exc)

    def do_batch(self, arg: str) -> None:
        "Score a generated batch. Example: batch 20 src=500..520 amount=1000..120000 shared_ip=true"
        try:
            parts = shlex.split(arg)
            if not parts:
                raise ValueError("batch requires a count")
            count = int(parts[0])
            results = self.session.score_batch(count, parse_assignments(" ".join(parts[1:])))
            print_batch_summary(results)
        except Exception as exc:
            print_error(exc)

    def do_set(self, arg: str) -> None:
        "Set default fields. Example: set channel=wallet_pay historical_risk=0.72 blacklist=none"
        try:
            self.session.set_defaults(parse_assignments(arg))
            print("defaults updated")
        except Exception as exc:
            print_error(exc)

    def do_json(self, arg: str) -> None:
        "Run a JSON command or score a JSON event payload."
        try:
            payload = json.loads(arg)
            if isinstance(payload, list):
                results = []
                for item in payload:
                    results.extend(self.session.run_command(item))
            elif isinstance(payload, dict):
                results = self.session.run_command(payload)
            else:
                raise ValueError("json command must be an object or list")
            print_batch_summary(results)
        except Exception as exc:
            print_error(exc)

    def do_load(self, arg: str) -> None:
        "Load JSON or JSONL commands from a file."
        try:
            path = Path(shlex.split(arg)[0])
            results = self.session.run_script(path)
            print_batch_summary(results)
        except Exception as exc:
            print_error(exc)

    def do_export(self, arg: str) -> None:
        "Export all results to a JSON file."
        try:
            path = Path(shlex.split(arg)[0])
            write_results(path, self.session.results)
            print(f"exported {len(self.session.results)} results to {path}")
        except Exception as exc:
            print_error(exc)

    def do_show(self, arg: str) -> None:
        "Show defaults, state, history, or last. Example: show last"
        target = (arg or "state").strip().lower()
        if target == "defaults":
            print_json(self.session.defaults)
        elif target == "history":
            print_history(self.session.results)
        elif target == "last":
            self.do_detail("-1")
        else:
            print_json(
                {
                    "next_event_id": self.session.next_event_id,
                    "next_timestamp": self.session.next_timestamp,
                    "result_count": len(self.session.results),
                }
            )

    def do_detail(self, arg: str) -> None:
        "Print a full result by index. Use detail -1 for the last result."
        try:
            index = int((arg or "-1").strip())
            result = self.session.results[index if index < 0 else index - 1]
            print_json(result)
        except Exception as exc:
            print_error(exc)

    def do_reset(self, arg: str) -> None:
        "Reset defaults, feature state, scorer state, and result history."
        del arg
        self.session.reset()
        print("session reset")

    def do_quit(self, arg: str) -> bool:
        "Exit the console."
        del arg
        return True

    def do_exit(self, arg: str) -> bool:
        "Exit the console."
        return self.do_quit(arg)

    def emptyline(self) -> None:
        return None


def run_manual_console(script_path: Path | None, output_path: Path | None, print_full_json: bool) -> None:
    session = ManualRiskSession()
    if script_path is None:
        RiskConsole(session).cmdloop()
        if output_path is not None:
            write_results(output_path, session.results)
        return
    results = session.run_script(script_path)
    if output_path is not None:
        write_results(output_path, results)
    if print_full_json:
        typer.echo(json.dumps({"results": results, "summary": aggregate_summary(results)}, ensure_ascii=False, indent=2))
    else:
        typer.echo(json.dumps(aggregate_summary(results), ensure_ascii=False, indent=2))


def normalize_updates(payload: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"type", "count", "defaults", "overrides", "fields"}:
            continue
        if key in {"transaction", "account", "device", "blacklist", "batch"} and isinstance(value, dict):
            merge_nested(nested.setdefault(key, {}), value)
            continue
        path = ALIASES.get(key, key)
        if "." not in path:
            path = f"transaction.{path}"
        set_path(nested, path, value)
    for item in ("defaults", "overrides", "fields"):
        value = payload.get(item)
        if isinstance(value, dict):
            merge_nested(nested, normalize_updates(value))
    return nested


def parse_assignments(arg: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for token in shlex.split(arg):
        if "=" not in token:
            raise ValueError(f"expected key=value token: {token}")
        key, raw_value = token.split("=", 1)
        result[key] = parse_value(raw_value)
    return result


def parse_value(value: str) -> Any:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    if ".." in stripped:
        start, end = stripped.split("..", 1)
        return {"range": [parse_scalar(start), parse_scalar(end)]}
    if "," in stripped:
        return [parse_value(item) for item in stripped.split(",")]
    return parse_scalar(stripped)


def parse_scalar(value: str) -> Any:
    try:
        if any(item in value for item in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def materialize(value: Any, *, index: int, count: int) -> Any:
    if isinstance(value, str) and ".." in value:
        return materialize(parse_value(value), index=index, count=count)
    if isinstance(value, dict):
        if "cycle" in value:
            items = value["cycle"]
            if not isinstance(items, list) or not items:
                raise ValueError("cycle must be a non-empty list")
            return materialize(items[index % len(items)], index=index, count=count)
        if "range" in value:
            start, end = value["range"]
            step = value.get("step")
            if step is not None:
                return start + index * step
            if isinstance(start, int) and isinstance(end, int):
                span = max(end - start + 1, 1)
                if count <= 1:
                    return start
                if span == count:
                    return start + index
                if span > count:
                    return int(round(start + (end - start) * index / (count - 1)))
                return start + index % span
            if count <= 1:
                return start
            return float(start) + (float(end) - float(start)) * index / (count - 1)
        return {key: materialize(item, index=index, count=count) for key, item in value.items()}
    if isinstance(value, list):
        if not value:
            return value
        return materialize(value[index % len(value)], index=index, count=count)
    return value


def merge_nested(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_nested(target[key], value)
        else:
            target[key] = value


def set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = target
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def load_script(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        commands = [json.loads(line) for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        return assert_command_list(commands)
    if isinstance(payload, dict) and "commands" in payload:
        commands = payload["commands"]
    else:
        commands = payload
    if isinstance(commands, dict):
        commands = [commands]
    return assert_command_list(commands)


def assert_command_list(commands: Any) -> list[dict[str, Any]]:
    if not isinstance(commands, list):
        raise ValueError("script must contain a command object or command list")
    result = []
    for item in commands:
        if not isinstance(item, dict):
            raise ValueError("each script command must be an object")
        result.append(item)
    return result


def score_breakdown(decision: RiskDecision) -> list[dict[str, Any]]:
    rows = []
    for key, weight in SCORE_WEIGHTS.items():
        value = float(decision.evidence.get(key, 0.0))
        rows.append(
            {
                "name": key,
                "weight": weight,
                "value": value,
                "contribution": value * weight,
            }
        )
    return rows


def concise_summary(decision: RiskDecision) -> dict[str, Any]:
    return {
        "event_id": decision.event_id,
        "src_account": decision.src_account,
        "dst_account": decision.dst_account,
        "risk_score": round(decision.risk_score, 6),
        "risk_level": decision.risk_level,
        "decision": decision.decision,
        "reason_codes": decision.reason_codes,
        "community_id": decision.community_id,
        "related_node_count": len(decision.related_nodes),
    }


def aggregate_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    levels: dict[str, int] = {}
    reasons: dict[str, int] = {}
    for result in results:
        decision = result["decision"]
        levels[decision["risk_level"]] = levels.get(decision["risk_level"], 0) + 1
        for reason in decision.get("reason_codes", []):
            reasons[reason] = reasons.get(reason, 0) + 1
    top = sorted(
        (result["summary"] for result in results),
        key=lambda item: (-float(item["risk_score"]), int(item["event_id"])),
    )[:10]
    return {
        "event_count": len(results),
        "risk_level_counts": dict(sorted(levels.items())),
        "reason_counts": dict(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        "top_events": top,
    }


def write_results(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"summary": aggregate_summary(results), "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_result_line(result: dict[str, Any]) -> None:
    summary = result["summary"]
    reasons = ",".join(summary["reason_codes"])
    print(
        f"event={summary['event_id']} score={summary['risk_score']:.6f} "
        f"level={summary['risk_level']} action={summary['decision']} reasons={reasons}"
    )


def print_batch_summary(results: list[dict[str, Any]]) -> None:
    if not results:
        print("no scored events")
        return
    summary = aggregate_summary(results)
    print_json(summary)


def print_history(results: list[dict[str, Any]], limit: int = 20) -> None:
    for result in results[-limit:]:
        print_result_line(result)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def print_error(exc: Exception) -> None:
    print(f"error: {exc}")
