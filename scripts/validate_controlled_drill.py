#!/usr/bin/env python3
"""Validate sanitized controlled-drill recovery evidence without executing a drill.

This validator is intentionally standard-library-only and fail-closed. It reads
one JSON record, performs no network or Kubernetes calls, and never approves,
injects, or cleans up a fault.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "controlled-drill-recovery.schema.json"
TARGET_SECONDS = 360
MIN_REPETITIONS = 3
CHECK_IDS = {
    "health",
    "api-crud",
    "canonical-pong-two-player-journey",
    "cleanup",
}
UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
PUBLIC_ENDPOINT_RE = re.compile(
    r"(?i)(?:https?://|\b(?:[a-z0-9-]+\.)*(?:belacca\.com|github\.com)\b|\b(?:public|live)[_-]?(?:endpoint|url|host)\b)"
)
SENSITIVE_VALUE_RE = re.compile(
    r"(?i)\b(?:bearer\s+\S+|eyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+)\b"
)


class ValidationError(Exception):
    """Raised for a malformed or unsafe evidence record."""


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def require_object(value: Any, path: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        fail(errors, f"{path} must be an object")
        return None
    return value


def require_keys(value: dict[str, Any], required: set[str], path: str, errors: list[str]) -> None:
    missing = sorted(required - value.keys())
    if missing:
        fail(errors, f"{path} missing required keys: {', '.join(missing)}")


def reject_extra_keys(value: dict[str, Any], allowed: set[str], path: str, errors: list[str]) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        fail(errors, f"{path} has unsupported keys: {', '.join(extra)}")


def require_string(value: Any, path: str, errors: list[str], *, nonempty: bool = True) -> None:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        fail(errors, f"{path} must be a non-empty string")


def require_bool(value: Any, expected: bool, path: str, errors: list[str]) -> None:
    if type(value) is not bool or value is not expected:
        fail(errors, f"{path} must be {str(expected).lower()}")


def parse_utc_timestamp(value: Any, path: str, errors: list[str]) -> dt.datetime | None:
    if not isinstance(value, str) or not UTC_TIMESTAMP_RE.fullmatch(value):
        fail(errors, f"{path} must be an RFC3339 UTC timestamp ending in Z")
        return None
    try:
        return dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        fail(errors, f"{path} is not a valid timestamp")
        return None


def check_exact_constant(value: Any, expected: Any, path: str, errors: list[str]) -> None:
    if value != expected or type(value) is not type(expected):
        fail(errors, f"{path} must equal {expected!r}")


def validate_safety(data: dict[str, Any], errors: list[str]) -> None:
    safety = require_object(data.get("safety"), "safety", errors)
    if safety is None:
        return
    allowed = {"approved", "approval", "bounded", "public_endpoint_targeted", "target_reference", "mutation_performed"}
    reject_extra_keys(safety, allowed, "safety", errors)
    require_keys(safety, allowed, "safety", errors)
    require_bool(safety.get("approved"), True, "safety.approved", errors)
    require_bool(safety.get("public_endpoint_targeted"), False, "safety.public_endpoint_targeted", errors)
    if not isinstance(safety.get("mutation_performed"), bool):
        fail(errors, "safety.mutation_performed must be boolean")
    target = safety.get("target_reference")
    require_string(target, "safety.target_reference", errors)
    if isinstance(target, str) and PUBLIC_ENDPOINT_RE.search(target):
        fail(errors, "safety.target_reference must not identify a live public endpoint")

    approval = require_object(safety.get("approval"), "safety.approval", errors)
    if approval is not None:
        allowed_approval = {"approver_role", "approved_at", "change_reference"}
        reject_extra_keys(approval, allowed_approval, "safety.approval", errors)
        require_keys(approval, allowed_approval, "safety.approval", errors)
        require_string(approval.get("approver_role"), "safety.approval.approver_role", errors)
        parse_utc_timestamp(approval.get("approved_at"), "safety.approval.approved_at", errors)
        require_string(approval.get("change_reference"), "safety.approval.change_reference", errors)

    bounded = require_object(safety.get("bounded"), "safety.bounded", errors)
    if bounded is not None:
        allowed_bounded = {"fault_scope", "abort_conditions", "rollback_or_cleanup_plan"}
        reject_extra_keys(bounded, allowed_bounded, "safety.bounded", errors)
        require_keys(bounded, allowed_bounded, "safety.bounded", errors)
        require_string(bounded.get("fault_scope"), "safety.bounded.fault_scope", errors)
        conditions = bounded.get("abort_conditions")
        if not isinstance(conditions, list) or not conditions or not all(isinstance(item, str) and item.strip() for item in conditions):
            fail(errors, "safety.bounded.abort_conditions must contain at least one non-empty string")
        require_string(bounded.get("rollback_or_cleanup_plan"), "safety.bounded.rollback_or_cleanup_plan", errors)


def validate_checks(
    repetition: dict[str, Any], path: str, start_time: dt.datetime | None,
    stop_time: dt.datetime | None, errors: list[str],
) -> bool:
    checks = repetition.get("recovery_checks")
    if not isinstance(checks, list) or len(checks) != 4:
        fail(errors, f"{path}.recovery_checks must contain exactly the four required checks")
        return False
    seen: set[str] = set()
    all_pass = True
    for index, raw_check in enumerate(checks):
        check_path = f"{path}.recovery_checks[{index}]"
        check = require_object(raw_check, check_path, errors)
        if check is None:
            continue
        allowed = {"id", "result", "observed_at", "evidence_reference", "exact_check", "not_applicable_reason"}
        reject_extra_keys(check, allowed, check_path, errors)
        require_keys(check, {"id", "result", "observed_at", "evidence_reference", "exact_check"}, check_path, errors)
        check_id = check.get("id")
        if check_id not in CHECK_IDS:
            fail(errors, f"{check_path}.id is not one of the required recovery checks")
        elif check_id in seen:
            fail(errors, f"{check_path}.id is duplicated")
        else:
            seen.add(check_id)
        result = check.get("result")
        if result not in {"pass", "fail", "not_applicable"}:
            fail(errors, f"{check_path}.result is invalid")
        elif result == "fail":
            all_pass = False
        observed_at = parse_utc_timestamp(check.get("observed_at"), f"{check_path}.observed_at", errors)
        if observed_at is not None and start_time is not None and observed_at < start_time:
            fail(errors, f"{check_path}.observed_at must not precede start.timestamp")
        if observed_at is not None and stop_time is not None and observed_at > stop_time:
            fail(errors, f"{check_path}.observed_at must not be after stop.timestamp")
        require_string(check.get("evidence_reference"), f"{check_path}.evidence_reference", errors)
        require_string(check.get("exact_check"), f"{check_path}.exact_check", errors)
        if result == "not_applicable":
            if check_id != "canonical-pong-two-player-journey":
                fail(errors, f"{check_path} only the canonical Pong journey may be not_applicable")
            require_string(check.get("not_applicable_reason"), f"{check_path}.not_applicable_reason", errors)
        elif "not_applicable_reason" in check:
            fail(errors, f"{check_path}.not_applicable_reason is only allowed for not_applicable")
    if seen != CHECK_IDS:
        fail(errors, f"{path}.recovery_checks must contain each required check exactly once")
    return all_pass and seen == CHECK_IDS


def validate_repetition(raw: Any, index: int, errors: list[str]) -> tuple[str | None, float | None, bool]:
    path = f"repetitions[{index}]"
    repetition = require_object(raw, path, errors)
    if repetition is None:
        return None, None, False
    allowed = {"id", "comparability_key", "fault_class", "start", "stop", "duration_seconds", "recovery_status", "recovery_checks", "impact", "runbook_revision", "follow_up_issue"}
    reject_extra_keys(repetition, allowed, path, errors)
    require_keys(repetition, allowed, path, errors)
    for key in ("id", "comparability_key", "fault_class", "impact", "runbook_revision"):
        require_string(repetition.get(key), f"{path}.{key}", errors)
    drill_id = repetition.get("id") if isinstance(repetition.get("id"), str) else None
    if drill_id is not None and not re.fullmatch(r"drill-[A-Za-z0-9._-]+", drill_id):
        fail(errors, f"{path}.id must match drill-<identifier>")

    start = require_object(repetition.get("start"), f"{path}.start", errors)
    stop = require_object(repetition.get("stop"), f"{path}.stop", errors)
    start_time = stop_time = None
    if start is not None:
        reject_extra_keys(start, {"kind", "timestamp", "evidence_reference"}, f"{path}.start", errors)
        require_keys(start, {"kind", "timestamp", "evidence_reference"}, f"{path}.start", errors)
        if start.get("kind") not in {"fault_injection", "confirmed_actionable_failure_alert"}:
            fail(errors, f"{path}.start.kind is invalid")
        start_time = parse_utc_timestamp(start.get("timestamp"), f"{path}.start.timestamp", errors)
        require_string(start.get("evidence_reference"), f"{path}.start.evidence_reference", errors)
    if stop is not None:
        reject_extra_keys(stop, {"timestamp", "evidence_reference"}, f"{path}.stop", errors)
        require_keys(stop, {"timestamp", "evidence_reference"}, f"{path}.stop", errors)
        stop_time = parse_utc_timestamp(stop.get("timestamp"), f"{path}.stop.timestamp", errors)
        require_string(stop.get("evidence_reference"), f"{path}.stop.evidence_reference", errors)

    duration = repetition.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        fail(errors, f"{path}.duration_seconds must be a finite positive number")
        duration_value = None
    else:
        duration_value = float(duration)
    if start_time is not None and stop_time is not None:
        elapsed = (stop_time - start_time).total_seconds()
        if elapsed <= 0:
            fail(errors, f"{path}.stop.timestamp must be after start.timestamp")
        elif duration_value is not None and not math.isclose(duration_value, elapsed, abs_tol=0.001):
            fail(errors, f"{path}.duration_seconds must equal stop minus start within 1ms")

    recovery_status = repetition.get("recovery_status")
    if recovery_status not in {"pass", "fail"}:
        fail(errors, f"{path}.recovery_status must be pass or fail")
    checks_pass = validate_checks(repetition, path, start_time, stop_time, errors)
    if recovery_status == "pass" and not checks_pass:
        fail(errors, f"{path}.recovery_status=pass requires every applicable recovery check to pass")
    if recovery_status == "fail" and checks_pass:
        fail(errors, f"{path}.recovery_status=fail requires at least one failed or not-applicable check")

    follow_up = repetition.get("follow_up_issue")
    if follow_up is not None and (not isinstance(follow_up, str) or not follow_up.strip()):
        fail(errors, f"{path}.follow_up_issue must be a non-empty issue reference or null")
    if (recovery_status == "fail" or (duration_value is not None and duration_value >= TARGET_SECONDS)) and follow_up is None:
        fail(errors, f"{path}.follow_up_issue is required for a recovery failure or duration at/over target")
    return repetition.get("comparability_key") if isinstance(repetition.get("comparability_key"), str) else None, duration_value, recovery_status == "pass"


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    record = require_object(data, "record", errors)
    if record is None:
        return errors
    allowed_top = {"$schema", "schema_version", "sanitized", "record_type", "objective", "environment", "safety", "repetitions", "evaluation", "limitations"}
    reject_extra_keys(record, allowed_top, "record", errors)
    require_keys(record, allowed_top, "record", errors)
    check_exact_constant(record.get("$schema"), "https://raw.githubusercontent.com/macel94/belacca-platform/main/docs/controlled-drill-recovery.schema.json", "$schema", errors)
    check_exact_constant(record.get("schema_version"), "belacca.controlled-drill-evidence.v1", "schema_version", errors)
    require_bool(record.get("sanitized"), True, "sanitized", errors)
    check_exact_constant(record.get("record_type"), "controlled_drill_batch", "record_type", errors)

    objective = require_object(record.get("objective"), "objective", errors)
    if objective is not None:
        allowed = {"id", "availability_slo", "recovery_target_seconds", "percentile", "comparison", "minimum_comparable_repetitions"}
        reject_extra_keys(objective, allowed, "objective", errors)
        require_keys(objective, allowed, "objective", errors)
        check_exact_constant(objective.get("id"), "belacca-controlled-drill-recovery-v1", "objective.id", errors)
        check_exact_constant(objective.get("recovery_target_seconds"), TARGET_SECONDS, "objective.recovery_target_seconds", errors)
        check_exact_constant(objective.get("percentile"), "P95", "objective.percentile", errors)
        check_exact_constant(objective.get("comparison"), "strictly_under", "objective.comparison", errors)
        check_exact_constant(objective.get("minimum_comparable_repetitions"), MIN_REPETITIONS, "objective.minimum_comparable_repetitions", errors)
        slo = require_object(objective.get("availability_slo"), "objective.availability_slo", errors)
        if slo is not None:
            allowed_slo = {"target_percent", "window", "sla", "separate_from_recovery_objective"}
            reject_extra_keys(slo, allowed_slo, "objective.availability_slo", errors)
            require_keys(slo, allowed_slo, "objective.availability_slo", errors)
            check_exact_constant(slo.get("target_percent"), "99%", "objective.availability_slo.target_percent", errors)
            check_exact_constant(slo.get("window"), "rolling_30d", "objective.availability_slo.window", errors)
            require_bool(slo.get("sla"), False, "objective.availability_slo.sla", errors)
            require_bool(slo.get("separate_from_recovery_objective"), True, "objective.availability_slo.separate_from_recovery_objective", errors)

    environment = require_object(record.get("environment"), "environment", errors)
    environment_scope = None
    environment_production = None
    if environment is not None:
        allowed = {"scope", "environment_reference", "production"}
        reject_extra_keys(environment, allowed, "environment", errors)
        require_keys(environment, allowed, "environment", errors)
        environment_scope = environment.get("scope")
        environment_production = environment.get("production")
        if environment_scope not in {"native-production-edge-control-plane-application", "isolated-capacity-chaos"}:
            fail(errors, "environment.scope is invalid")
        require_string(environment.get("environment_reference"), "environment.environment_reference", errors)
        if not isinstance(environment_production, bool):
            fail(errors, "environment.production must be boolean")
        elif (environment_scope == "isolated-capacity-chaos") != (environment_production is False):
            fail(errors, "isolated-capacity-chaos must set production=false, and native-production scope must set production=true")

    validate_safety(record, errors)
    repetitions = record.get("repetitions")
    if not isinstance(repetitions, list) or not repetitions:
        fail(errors, "repetitions must contain at least one record")
        repetitions = []
    comparability: list[tuple[str, str, str]] = []
    durations: list[float] = []
    passing: list[bool] = []
    ids: set[str] = set()
    for index, repetition in enumerate(repetitions):
        key, duration, passed = validate_repetition(repetition, index, errors)
        if isinstance(repetition, dict) and key is not None:
            comparability.append((
                key,
                repetition.get("fault_class") if isinstance(repetition.get("fault_class"), str) else "",
                repetition.get("runbook_revision") if isinstance(repetition.get("runbook_revision"), str) else "",
            ))
        if duration is not None:
            durations.append(duration)
        passing.append(passed)
        if isinstance(repetition, dict) and isinstance(repetition.get("id"), str):
            if repetition["id"] in ids:
                fail(errors, f"repetitions[{index}].id is duplicated")
            ids.add(repetition["id"])
    if comparability and len(set(comparability)) != 1:
        fail(errors, "all repetitions in a batch must share comparability_key, fault_class, and runbook_revision")

    evaluation = require_object(record.get("evaluation"), "evaluation", errors)
    if evaluation is not None:
        allowed = {"comparable_repetition_count", "p95_method", "p95_duration_seconds", "target_status", "claimable"}
        reject_extra_keys(evaluation, allowed, "evaluation", errors)
        require_keys(evaluation, allowed, "evaluation", errors)
        count = evaluation.get("comparable_repetition_count")
        if type(count) is not int or count != len(repetitions):
            fail(errors, "evaluation.comparable_repetition_count must equal the repetition count")
        check_exact_constant(evaluation.get("p95_method"), "nearest_rank", "evaluation.p95_method", errors)
        expected_claimable = len(repetitions) >= MIN_REPETITIONS
        if type(evaluation.get("claimable")) is not bool or evaluation.get("claimable") != expected_claimable:
            fail(errors, "evaluation.claimable must be true only with at least three comparable repetitions")
        expected_p95 = None
        if durations:
            ordered = sorted(durations)
            rank = max(1, math.ceil(0.95 * len(ordered)))
            expected_p95 = ordered[rank - 1]
        actual_p95 = evaluation.get("p95_duration_seconds")
        if expected_p95 is None:
            if actual_p95 is not None:
                fail(errors, "evaluation.p95_duration_seconds must be null without valid durations")
        elif isinstance(actual_p95, bool) or not isinstance(actual_p95, (int, float)) or not math.isclose(float(actual_p95), expected_p95, abs_tol=0.001):
            fail(errors, "evaluation.p95_duration_seconds does not match nearest-rank P95")
        status = evaluation.get("target_status")
        expected_status = "not_claimed" if not expected_claimable else ("pass" if all(passing) and expected_p95 is not None and expected_p95 < TARGET_SECONDS else "fail")
        if status != expected_status:
            fail(errors, f"evaluation.target_status must be {expected_status!r}")

    limitations = record.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(isinstance(item, str) and item.strip() for item in limitations):
        fail(errors, "limitations must contain at least one non-empty string")

    serialized = json.dumps(record, ensure_ascii=False)
    if SENSITIVE_VALUE_RE.search(serialized):
        fail(errors, "record contains a token-shaped or bearer credential value")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate controlled-drill evidence without executing a drill.")
    parser.add_argument("record", type=Path, help="JSON evidence record to validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid evidence JSON: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        print(f"controlled-drill evidence rejected: {len(errors)} error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"controlled-drill evidence valid: {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
