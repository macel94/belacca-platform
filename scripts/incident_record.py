#!/usr/bin/env python3
"""Create and validate sanitized incident records.

This tool only writes a local incident record. It never contacts GitHub, the
cluster, Flux, or a notification system. Evidence attachment copies source
metadata and timestamps from a collector bundle while deliberately omitting
all command output.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "incidents"
SCHEMA_VERSION = "belacca.incident-record.v1"
STATES = ("declared", "active", "monitoring", "resolved", "closed")
SEVERITIES = ("SEV-1", "SEV-2", "SEV-3", "SEV-4")
SOURCE_STATUSES = ("ok", "failed", "unavailable", "timed_out", "truncated", "incomplete")
ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,63}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
UNSAFE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b"),
    re.compile(r"\bBearer\s+[^\s,;]+", re.I),
    re.compile(
        r"(?:password|passwd|passphrase|pwd|token|authorization|cookie|"
        r"private[_-]?key|client[_-]?secret|api[_-]?key|access[_-]?key|credential)"
        r"\s*[:=]\s*(?![`\[]?(?:REDACTED|unknown|none|TBD)\b)[^\s,;}`\]]+",
        re.I,
    ),
    re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])"),
    re.compile(r"(?<![\w:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])"),
)


class RecordError(ValueError):
    """Raised for invalid or unsafe record input."""


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def timestamp(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_timestamp(value: str) -> str:
    if not isinstance(value, str) or not ISO_RE.fullmatch(value):
        raise RecordError(f"invalid UTC timestamp: {value!r}")
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecordError(f"invalid UTC timestamp: {value!r}") from exc
    return value


def assert_safe_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecordError(f"{field} must be non-empty text")
    for pattern in UNSAFE_PATTERNS:
        if pattern.search(value):
            raise RecordError(f"{field} contains sensitive or private telemetry; record only sanitized text")
    return value.strip()


def walk_strings(value: Any, path: str = "record") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def validate_safety(record: dict[str, Any]) -> None:
    for path, value in walk_strings(record):
        for pattern in UNSAFE_PATTERNS:
            if pattern.search(value):
                raise RecordError(f"{path} contains sensitive or private telemetry")


def empty_record(
    record_id: str, title: str, severity: str, declared_at: str,
    commander: str, operations: str, communications: str, planning: str,
) -> dict[str, Any]:
    if not ID_RE.fullmatch(record_id):
        raise RecordError("id must match [A-Z0-9][A-Z0-9_-]{2,63}")
    if severity not in SEVERITIES:
        raise RecordError(f"severity must be one of: {', '.join(SEVERITIES)}")
    title = assert_safe_text(title, "title")
    roles = {
        "incident_commander": assert_safe_text(commander, "commander"),
        "operations_lead": assert_safe_text(operations, "operations lead"),
        "communications_lead": assert_safe_text(communications, "communications lead"),
        "planning_follow_up_lead": assert_safe_text(planning, "planning/follow-up lead"),
    }
    declared_at = parse_timestamp(declared_at)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "title": title,
        "state": "declared",
        "severity": severity,
        "declared_at": declared_at,
        "last_updated_at": declared_at,
        "roles": roles,
        "record_control": {
            "single_writer_role": "incident_commander",
            "rule": "Only the named single writer edits the canonical incident record; responders submit observations to that writer.",
            "direct_cluster_mutation_allowed": False,
            "human_approval_required": True,
            "gitops_only_production_changes": True,
        },
        "impact": {
            "affected_service_or_journey": "unknown",
            "summary": "unknown",
            "scope": "unknown",
            "started_at": "unknown",
            "recovery_at": "unknown",
        },
        "evidence": {"bundle_ids": [], "sources": []},
        "timeline": [{
            "at": declared_at,
            "event": "Incident declared; severity and roles assigned.",
            "actor_role": "incident_commander",
            "evidence_refs": [],
        }],
        "hypotheses": [],
        "actions": [],
        "handoffs": [],
        "communications": [],
        "postmortem": {
            "decision": "pending",
            "triggers": [],
            "record": None,
            "review_status": "not_started",
        },
        "closure": {
            "criteria": {
                "impact_ended_or_unknown": False,
                "recovery_observed_or_limitation_recorded": False,
                "monitoring_active_and_limited": False,
                "actions_complete_cancelled_or_owned": False,
                "communications_complete": False,
                "postmortem_decision_recorded": False,
                "ic_and_planning_reviewed": False,
            },
            "closed_at": None,
            "closed_by": None,
        },
        "safety": {
            "sanitized": True,
            "prohibited_content": [
                "secrets", "player data", "tokens", "credentials", "unredacted private telemetry",
            ],
            "raw_evidence_embedded": False,
        },
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RecordError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def source_ref_ids(record: dict[str, Any]) -> set[str]:
    return {str(source["source_id"]) for source in record["evidence"]["sources"]}


def validate_record(record: dict[str, Any]) -> None:
    required = ("schema_version", "record_id", "title", "state", "severity", "declared_at", "roles", "record_control", "evidence", "timeline", "safety")
    missing = [key for key in required if key not in record]
    if missing:
        raise RecordError(f"missing required fields: {', '.join(missing)}")
    if record["schema_version"] != SCHEMA_VERSION:
        raise RecordError(f"unsupported schema_version: {record['schema_version']!r}")
    if not isinstance(record["record_id"], str) or not ID_RE.fullmatch(record["record_id"]):
        raise RecordError("record_id has invalid format")
    assert_safe_text(record["title"], "title")
    if record["state"] not in STATES:
        raise RecordError(f"invalid state: {record['state']!r}")
    if record["severity"] not in SEVERITIES:
        raise RecordError(f"invalid severity: {record['severity']!r}")
    parse_timestamp(record["declared_at"])
    parse_timestamp(record.get("last_updated_at", record["declared_at"]))
    roles = record["roles"]
    if not isinstance(roles, dict):
        raise RecordError("roles must be an object")
    for role in ("incident_commander", "operations_lead", "communications_lead", "planning_follow_up_lead"):
        assert_safe_text(roles.get(role, ""), f"roles.{role}")
    control = record["record_control"]
    if not isinstance(control, dict) or control.get("single_writer_role") not in roles:
        raise RecordError("record_control must name one of the four role keys as single_writer_role")
    if control.get("direct_cluster_mutation_allowed") is not False:
        raise RecordError("direct cluster mutation must remain false")
    if control.get("human_approval_required") is not True or control.get("gitops_only_production_changes") is not True:
        raise RecordError("human approval and GitOps-only production controls are required")
    evidence = record["evidence"]
    if not isinstance(evidence, dict) or not isinstance(evidence.get("sources"), list):
        raise RecordError("evidence.sources must be a list")
    seen: set[str] = set()
    for source in evidence["sources"]:
        if not isinstance(source, dict):
            raise RecordError("each evidence source must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id or source_id in seen:
            raise RecordError("evidence source IDs must be non-empty and unique")
        seen.add(source_id)
        parse_timestamp(source.get("evidence_timestamp", ""))
        if source.get("status") not in SOURCE_STATUSES:
            raise RecordError(f"invalid evidence status for {source_id}")
        assert_safe_text(source.get("observation", ""), f"evidence.{source_id}.observation")
        if "raw_output" in source or "command_output" in source:
            raise RecordError(f"raw output is not allowed in evidence source {source_id}")
    for event in record.get("timeline", []):
        if not isinstance(event, dict):
            raise RecordError("timeline entries must be objects")
        parse_timestamp(event.get("at", ""))
        refs = event.get("evidence_refs", [])
        if not isinstance(refs, list) or not set(refs).issubset(seen):
            raise RecordError("timeline evidence_refs must point to attached source IDs")
    if not isinstance(record.get("safety"), dict) or record["safety"].get("sanitized") is not True or record["safety"].get("raw_evidence_embedded") is not False:
        raise RecordError("sanitized safety assertions are required")
    validate_safety(record)


def attach_bundle(record: dict[str, Any], bundle: dict[str, Any]) -> int:
    validate_record(record)
    if not bundle.get("bundle_id") or not isinstance(bundle.get("sources"), list):
        raise RecordError("bundle must contain bundle_id and sources")
    existing = source_ref_ids(record)
    additions = 0
    for source in bundle["sources"]:
        if not isinstance(source, dict) or not source.get("id"):
            raise RecordError("bundle contains a source without an id")
        source_id = str(source["id"])
        if source_id in existing:
            continue
        status = str(source.get("status", "incomplete"))
        if status not in SOURCE_STATUSES:
            status = "incomplete"
        evidence_timestamp = parse_timestamp(str(source.get("evidence_timestamp", "")))
        record["evidence"]["sources"].append({
            "source_id": source_id,
            "evidence_timestamp": evidence_timestamp,
            "status": status,
            "completeness": "complete" if status == "ok" and not source.get("truncated") else "incomplete",
            "observation": f"Bounded collector source completed with status `{status}`; raw output intentionally omitted from the incident record.",
        })
        additions += 1
    bundle_id = str(bundle["bundle_id"])
    if bundle_id not in record["evidence"]["bundle_ids"]:
        record["evidence"]["bundle_ids"].append(bundle_id)
    now = timestamp(utc_now())
    record["last_updated_at"] = now
    record["timeline"].append({
        "at": now,
        "event": f"Attached sanitized source metadata from evidence bundle {bundle_id}; raw output was not copied.",
        "actor_role": "planning_follow_up_lead",
        "evidence_refs": [source["source_id"] for source in record["evidence"]["sources"]],
    })
    return additions


def markdown_record(record: dict[str, Any]) -> str:
    roles = record["roles"]
    lines = [
        f"# Incident state — `{record['record_id']}` — {record['title']}", "",
        f"- **State:** `{record['state']}`", f"- **Severity:** `{record['severity']}`",
        f"- **Declared at (UTC):** `{record['declared_at']}`", f"- **Last updated at (UTC):** `{record['last_updated_at']}`",
        f"- **Incident Commander:** {roles['incident_commander']}", f"- **Operations Lead:** {roles['operations_lead']}",
        f"- **Communications Lead:** {roles['communications_lead']}", f"- **Planning/Follow-up Lead:** {roles['planning_follow_up_lead']}", "",
        "## Change control", "",
        f"- **Single writer:** `{record['record_control']['single_writer_role']}` ({roles[record['record_control']['single_writer_role']]})",
        f"- **Rule:** {record['record_control']['rule']}",
        "- **Direct cluster mutation:** **not allowed**; production changes are human-approved GitOps changes.", "",
        "## Impact", "",
        f"- **Service/journey:** {record['impact']['affected_service_or_journey']}", f"- **Summary:** {record['impact']['summary']}",
        f"- **Scope:** {record['impact']['scope']}", f"- **Started/recovered:** {record['impact']['started_at']} / {record['impact']['recovery_at']}", "",
        "## Evidence index", "", "| Source ID | Evidence timestamp (UTC) | Status | Completeness | Sanitized observation |", "|---|---|---|---|---|",
    ]
    for source in record["evidence"]["sources"]:
        lines.append(f"| `{source['source_id']}` | `{source['evidence_timestamp']}` | `{source['status']}` | `{source['completeness']}` | {source['observation']} |")
    if not record["evidence"]["sources"]:
        lines.append("| _none attached_ | — | — | — | Attach a reviewed evidence bundle; do not paste raw output. |")
    lines.extend(["", "## Timeline (UTC)", "", "| Time | Event | Role | Evidence refs |", "|---|---|---|---|"])
    for event in record["timeline"]:
        lines.append(f"| `{event['at']}` | {event['event']} | `{event['actor_role']}` | `{', '.join(event['evidence_refs']) or 'none'}` |")
    lines.extend(["", "## Postmortem decision", "", f"- **Decision:** `{record['postmortem']['decision']}`", f"- **Review status:** `{record['postmortem']['review_status']}`", "", "## Safety", "", "This record is sanitized. It contains no secrets, player data, tokens, credentials, or unredacted private telemetry. Evidence source output is never embedded.", ""])
    return "\n".join(lines)


def record_paths(output_dir: Path, record_id: str) -> tuple[Path, Path]:
    base = output_dir / f"incident-{record_id}"
    return base.with_suffix(".json"), base.with_suffix(".md")


def start(args: argparse.Namespace) -> int:
    commander = args.commander
    operations = args.operations or f"{commander} (temporary; delegate before active response)"
    communications = args.communications or f"{commander} (temporary; delegate before active response)"
    planning = args.planning or f"{commander} (temporary; delegate before active response)"
    record = empty_record(args.id, args.title, args.severity, args.declared_at or timestamp(utc_now()), commander, operations, communications, planning)
    validate_record(record)
    json_path, markdown_path = record_paths(args.output_dir, args.id)
    if json_path.exists() or markdown_path.exists():
        raise RecordError(f"refusing to overwrite existing record: {json_path}")
    write_json(json_path, record)
    markdown_path.write_text(markdown_record(record), encoding="utf-8")
    print(json_path)
    print(markdown_path)
    return 0


def attach(args: argparse.Namespace) -> int:
    record_path = args.record
    record = load_json(record_path)
    bundle = load_json(args.bundle)
    additions = attach_bundle(record, bundle)
    validate_record(record)
    write_json(record_path, record)
    record_path.with_suffix(".md").write_text(markdown_record(record), encoding="utf-8")
    print(f"attached {additions} source(s) to {record_path}")
    return 0


def validate_command(args: argparse.Namespace) -> int:
    record = load_json(args.record)
    validate_record(record)
    print(f"valid sanitized incident record: {args.record}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and validate sanitized incident records.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    start_parser = subparsers.add_parser("start", help="write a new local incident record")
    start_parser.add_argument("--id", required=True, type=str.upper)
    start_parser.add_argument("--title", required=True)
    start_parser.add_argument("--severity", choices=SEVERITIES, required=True)
    start_parser.add_argument("--commander", required=True)
    start_parser.add_argument("--operations")
    start_parser.add_argument("--communications")
    start_parser.add_argument("--planning")
    start_parser.add_argument("--declared-at")
    start_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    start_parser.set_defaults(handler=start)
    attach_parser = subparsers.add_parser("attach-bundle", help="attach source IDs/timestamps without copying output")
    attach_parser.add_argument("--record", type=Path, required=True)
    attach_parser.add_argument("--bundle", type=Path, required=True)
    attach_parser.set_defaults(handler=attach)
    validate_parser = subparsers.add_parser("validate", help="validate one sanitized incident record")
    validate_parser.add_argument("--record", type=Path, required=True)
    validate_parser.set_defaults(handler=validate_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except RecordError as exc:
        print(f"incident-record: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
