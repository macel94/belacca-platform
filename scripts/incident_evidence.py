#!/usr/bin/env python3
"""Collect a bounded, redacted, read-only incident evidence bundle."""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import re
import selectors
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "incident-evidence"
MAX_TIMEOUT_SECONDS = 60.0
MAX_OUTPUT_BYTES = 1_048_576
REDACTED = "[REDACTED]"
SOURCE_GROUPS = ("kubectl", "flux", "status")

# Fixed status reads only. Never add exec, apply, delete, patch, port-forward,
# reconciliation, or Secret-fetch commands to this list.
SOURCE_SPECS = (
    {
        "id": "kubectl-pods",
        "group": "kubectl",
        "command": ("kubectl", "get", "pods", "--all-namespaces", "--output=json"),
        "reference": "https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/",
    },
    {
        "id": "kubectl-deployments",
        "group": "kubectl",
        "command": ("kubectl", "get", "deployments", "--all-namespaces", "--output=json"),
        "reference": "https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/",
    },
    {
        "id": "kubectl-events",
        "group": "kubectl",
        "command": (
            "kubectl", "get", "events", "--all-namespaces",
            "--sort-by=.lastTimestamp", "--output=json",
        ),
        "reference": "https://kubernetes.io/docs/reference/kubectl/generated/kubectl_get/",
    },
    {
        "id": "flux-sources",
        "group": "flux",
        "command": ("flux", "get", "sources", "--all-namespaces", "--no-header"),
        "reference": "https://fluxcd.io/flux/cmd/flux_get/",
    },
    {
        "id": "flux-kustomizations",
        "group": "flux",
        "command": ("flux", "get", "kustomizations", "--all-namespaces", "--no-header"),
        "reference": "https://fluxcd.io/flux/cmd/flux_get/",
    },
    {
        "id": "status-parent",
        "group": "status",
        "command": ("git", "status", "--short", "--branch"),
        "reference": "scripts/status.sh (read-only workspace status equivalent)",
    },
    {
        "id": "status-site",
        "group": "status",
        "command": ("git", "-C", "francesco-belacca-site", "status", "--short", "--branch"),
        "reference": "scripts/status.sh (read-only workspace status equivalent)",
    },
    {
        "id": "status-submodules",
        "group": "status",
        "command": ("git", "submodule", "status"),
        "reference": "scripts/status.sh (read-only workspace status equivalent)",
    },
)

SENSITIVE_KEY_RE = re.compile(
    r"(?:secret|token|password|passwd|passphrase|pwd|authorization|cookie|"
    r"private[_-]?key|client[_-]?secret|api[_-]?key|access[_-]?key|credential)",
    re.IGNORECASE,
)
SENSITIVE_DATA_KEYS = {"data", "stringdata"}
CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?P<prefix>\"?(?P<key>secret|token|password|passwd|passphrase|pwd|"
    r"authorization|cookie|private[_-]?key|client[_-]?secret|api[_-]?key|"
    r"access[_-]?key|credential)\"?\s*[:=]\s*)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;}\]]+)",
    re.IGNORECASE,
)
CLI_CREDENTIAL_RE = re.compile(
    r"(?P<prefix>--(?:token|password|client-key|client-certificate)\s+)"
    r"(?P<value>[^\s]+)", re.IGNORECASE,
)
BEARER_RE = re.compile(r"(?i)(\bBearer\s+)[^\s,;]+")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b")
PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
IPV4_RE = re.compile(r"(?<![\w.])(?P<ip>(?:\d{1,3}\.){3}\d{1,3})(?![\w.])")
IPV6_RE = re.compile(r"(?<![\w:])(?P<ip>(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4})(?![\w:])")


@dataclass(frozen=True)
class CommandResult:
    returncode: int | None
    stdout: str
    stderr: str
    status: str
    timed_out: bool = False
    truncated: bool = False


Runner = Callable[[Sequence[str], float, int], CommandResult]


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_timestamp(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            process.kill()
        except ProcessLookupError:
            pass


def run_bounded(command: Sequence[str], timeout_seconds: float, max_bytes: int) -> CommandResult:
    """Run one fixed command with timeout and combined stdout/stderr bounds."""
    try:
        process = subprocess.Popen(
            list(command), cwd=REPO_ROOT, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        return CommandResult(None, "", f"{exc.filename}: command not found", "unavailable")
    except OSError as exc:
        return CommandResult(None, "", f"unable to start command: {exc}", "unavailable")

    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    streams: dict[int, tuple[object, bytearray, str]] = {
        process.stdout.fileno(): (process.stdout, bytearray(), "stdout"),
        process.stderr.fileno(): (process.stderr, bytearray(), "stderr"),
    }
    completed = {"stdout": bytearray(), "stderr": bytearray()}
    for fd in streams:
        selector.register(fd, selectors.EVENT_READ)

    total = 0
    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    truncated = False
    try:
        while streams and not timed_out and not truncated:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                _kill_process_group(process)
                break
            events = selector.select(min(remaining, 0.2))
            if not events:
                continue
            for event, _ in events:
                fd = event.fd
                file_object, buffer, name = streams[fd]
                try:
                    chunk = os.read(fd, min(8192, max_bytes - total + 1))
                except OSError:
                    chunk = b""
                if not chunk:
                    completed[name].extend(buffer)
                    selector.unregister(fd)
                    streams.pop(fd, None)
                    file_object.close()  # type: ignore[union-attr]
                    continue
                allowed = max(0, max_bytes - total)
                buffer.extend(chunk[:allowed])
                total += min(len(chunk), allowed)
                if len(chunk) > allowed:
                    truncated = True
                    _kill_process_group(process)
                    break
    finally:
        if timed_out or truncated:
            for fd, (file_object, buffer, name) in list(streams.items()):
                completed[name].extend(buffer)
                try:
                    selector.unregister(fd)
                except Exception:
                    pass
                file_object.close()  # type: ignore[union-attr]
            streams.clear()
        selector.close()

    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        _kill_process_group(process)
        process.wait(timeout=1)

    status = "timed_out" if timed_out else "truncated" if truncated else "ok" if process.returncode == 0 else "failed"
    return CommandResult(
        process.returncode,
        completed["stdout"].decode("utf-8", errors="replace"),
        completed["stderr"].decode("utf-8", errors="replace"),
        status, timed_out, truncated,
    )


def _increment(counts: dict[str, int], category: str) -> str:
    counts[category] = counts.get(category, 0) + 1
    return REDACTED


def _redact_ipv4(match: re.Match[str], counts: dict[str, int]) -> str:
    candidate = match.group("ip")
    return _increment(counts, "ip") if all(int(part) <= 255 for part in candidate.split(".")) else candidate


def _redact_ipv6(match: re.Match[str], counts: dict[str, int]) -> str:
    try:
        ipaddress.ip_address(match.group("ip"))
    except ValueError:
        return match.group("ip")
    return _increment(counts, "ip")


def _redact_credential(match: re.Match[str], counts: dict[str, int]) -> str:
    value = match.group("value")
    replacement = _increment(counts, "secret")
    if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
        replacement = value[0] + replacement + value[0]
    return match.group("prefix") + replacement


def redact_text(value: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    value = PRIVATE_KEY_RE.sub(lambda _: _increment(counts, "secret"), value)
    value = JWT_RE.sub(lambda _: _increment(counts, "token"), value)
    value = BEARER_RE.sub(lambda match: match.group(1) + _increment(counts, "token"), value)
    value = CREDENTIAL_ASSIGNMENT_RE.sub(lambda match: _redact_credential(match, counts), value)
    value = CLI_CREDENTIAL_RE.sub(lambda match: match.group("prefix") + _increment(counts, "token"), value)
    value = IPV4_RE.sub(lambda match: _redact_ipv4(match, counts), value)
    value = IPV6_RE.sub(lambda match: _redact_ipv6(match, counts), value)
    return value, counts


def redact_json(value: object, counts: dict[str, int] | None = None) -> object:
    counts = counts if counts is not None else {}
    if isinstance(value, dict):
        result: dict[object, object] = {}
        kind = str(value.get("kind", "")).lower()
        for key, child in value.items():
            key_text = str(key)
            if SENSITIVE_KEY_RE.search(key_text) or key_text.lower() in SENSITIVE_DATA_KEYS or (kind == "secret" and key_text.lower() in SENSITIVE_DATA_KEYS):
                result[key] = _increment(counts, "secret")
            else:
                result[key] = redact_json(child, counts)
        return result
    if isinstance(value, list):
        return [redact_json(child, counts) for child in value]
    if isinstance(value, str):
        redacted, text_counts = redact_text(value)
        for key, count in text_counts.items():
            counts[key] = counts.get(key, 0) + count
        return redacted
    return value


def sanitize_output(raw: str) -> tuple[str, dict[str, int], str]:
    redacted_text, counts = redact_text(raw)
    try:
        parsed = json.loads(redacted_text)
    except (json.JSONDecodeError, TypeError):
        return redacted_text, counts, "text"
    parsed_counts: dict[str, int] = {}
    parsed = redact_json(parsed, parsed_counts)
    for key, count in parsed_counts.items():
        counts[key] = counts.get(key, 0) + count
    return json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False), counts, "json"


def _safe_command(command: Sequence[str]) -> bool:
    if not command:
        return False
    if command[0] == "kubectl":
        return len(command) >= 3 and command[1] == "get" and "secret" not in command[2].lower()
    if command[0] == "flux":
        return len(command) >= 3 and command[1] == "get"
    if command[0] == "git":
        return list(command[1:]) in (
            ["status", "--short", "--branch"],
            ["-C", "francesco-belacca-site", "status", "--short", "--branch"],
            ["submodule", "status"],
        )
    return False


if not all(_safe_command(spec["command"]) for spec in SOURCE_SPECS):
    raise RuntimeError("unsafe command entered the evidence source allowlist")


def source_specs(groups: Iterable[str]) -> list[dict[str, object]]:
    selected = set(groups)
    return [spec for spec in SOURCE_SPECS if str(spec["group"]) in selected]


def collect_bundle(
    groups: Iterable[str], timeout_seconds: float = 15.0,
    max_bytes: int = 262_144, runner: Runner = run_bounded,
) -> dict[str, object]:
    collection_started = utc_now()
    sources: list[dict[str, object]] = []
    for spec in source_specs(groups):
        requested_at = utc_now()
        command = tuple(spec["command"])  # type: ignore[arg-type]
        result = runner(command, timeout_seconds, max_bytes) if _safe_command(command) else CommandResult(None, "", "source rejected by read-only allowlist", "unsafe")
        completed_at = utc_now()
        stdout, stdout_redactions, stdout_format = sanitize_output(result.stdout)
        stderr, stderr_redactions, _ = sanitize_output(result.stderr)
        redactions: dict[str, int] = {}
        for counts in (stdout_redactions, stderr_redactions):
            for key, count in counts.items():
                redactions[key] = redactions.get(key, 0) + count
        sources.append({
            "id": spec["id"], "category": spec["group"], "command": shlex.join(command),
            "read_only": True, "evidence_timestamp": iso_timestamp(completed_at),
            "requested_at": iso_timestamp(requested_at), "completed_at": iso_timestamp(completed_at),
            "status": result.status, "exit_code": result.returncode,
            "timed_out": result.timed_out, "truncated": result.truncated,
            "source_reference": spec["reference"], "output_format": stdout_format,
            "stdout": stdout, "stderr": stderr, "redactions": redactions,
        })

    collection_finished = utc_now()
    source_ids = [str(source["id"]) for source in sources]
    incomplete_ids = [str(source["id"]) for source in sources if source["status"] != "ok"]
    hypotheses: list[dict[str, object]] = [{
        "id": "H1",
        "statement": "This bounded snapshot cannot establish uptime or root cause by itself.",
        "confidence": "high", "confidence_score": 0.99, "evidence_refs": source_ids,
    }]
    hypotheses.append({
        "id": "H2",
        "statement": "The evidence set is incomplete because one or more requested inputs were unavailable, failed, timed out, or were truncated." if incomplete_ids else "The collected outputs describe observations at their recorded timestamps, not a continuous availability measurement.",
        "confidence": "high", "confidence_score": 0.98,
        "evidence_refs": incomplete_ids or source_ids,
    })
    finished_at = iso_timestamp(collection_finished)
    return {
        "schema_version": "belacca.incident-evidence.v1",
        "bundle_id": "incident-" + collection_finished.strftime("%Y%m%dT%H%M%S%fZ"),
        "generated_at": finished_at, "collection_started_at": iso_timestamp(collection_started),
        "collection_finished_at": finished_at, "read_only": True,
        "cluster_mutation_attempted": False, "scope": sorted(set(groups)),
        "limits": {"source_count": len(sources), "max_output_bytes_combined_per_source": max_bytes, "timeout_seconds_per_source": timeout_seconds},
        "redaction_policy": {
            "applied_before_emission": True,
            "categories": ["Secret/data fields", "token/password/credential-like values", "IP-like values", "private keys", "JWTs"],
            "note": "Only the bounded allowlist is queried. Redaction reduces exposure but is not a substitute for human review before sharing.",
        },
        "sources": sources, "hypotheses": hypotheses,
        "human_approved_actions": [
            {"id": "A1", "action": "Human reviewer: record the approved next step, owner, and expiry here.", "status": "pending_human_approval", "approved_by": None, "approved_at": None, "evidence_refs": []},
            {"id": "A2", "action": "If a production change is warranted, propose and review a GitOps-only change; do not execute cluster mutation from this bundle tool.", "status": "pending_human_approval", "approved_by": None, "approved_at": None, "evidence_refs": source_ids},
        ],
        "ai_assistance_boundary": {"read_only": True, "evidence_linked": True, "human_approval_required": True, "gitops_only_changes": True, "no_action_taken": True},
    }


def markdown_bundle(bundle: dict[str, object]) -> str:
    lines = [
        "# Incident evidence bundle", "", f"- Bundle ID: `{bundle['bundle_id']}`",
        f"- Generated at: `{bundle['generated_at']}`", f"- Scope: `{', '.join(bundle['scope'])}`",
        "- Read-only: **yes**", "- Cluster mutation attempted: **no**", "",
        "## Safety boundary", "",
        "This is a bounded observation snapshot. It is not an uptime claim, incident diagnosis, or approval to change production. Outputs were redacted before emission; review them before sharing.", "",
        "## Sources", "",
    ]
    for source in bundle["sources"]:  # type: ignore[union-attr]
        lines.extend([
            f"### `{source['id']}` — {source['status']}", "",
            f"- Evidence timestamp: `{source['evidence_timestamp']}`",
            f"- Requested: `{source['requested_at']}`; completed: `{source['completed_at']}`",
            f"- Command: `{source['command']}`", f"- Source reference: `{source['source_reference']}`",
            f"- Exit code: `{source['exit_code']}`; timed out: `{source['timed_out']}`; truncated: `{source['truncated']}`",
            f"- Redactions: `{json.dumps(source['redactions'], sort_keys=True)}`", "",
            "#### Redacted stdout", "", "```text", str(source["stdout"]).replace("```", "'''"), "```", "",
        ])
        if source["stderr"]:
            lines.extend(["#### Redacted stderr", "", "```text", str(source["stderr"]).replace("```", "'''"), "```", ""])
    lines.extend(["## Hypotheses", ""])
    for hypothesis in bundle["hypotheses"]:  # type: ignore[union-attr]
        lines.extend([f"- **{hypothesis['id']}** — {hypothesis['statement']}", f"  - Confidence: `{hypothesis['confidence']}` ({hypothesis['confidence_score']})", f"  - Evidence refs: `{', '.join(hypothesis['evidence_refs'])}`"])
    lines.extend(["", "## Human-approved actions", "", "No action is approved by this bundle.", ""])
    for action in bundle["human_approved_actions"]:  # type: ignore[union-attr]
        lines.append(f"- [ ] **{action['id']}** — {action['action']} (`{action['status']}`)")
    lines.extend(["", "## AI-assistance boundary", "", "- Read-only collection only.", "- Every hypothesis must link to evidence refs and remains a hypothesis.", "- A human must approve any action.", "- Production changes are GitOps-only, reviewed changes; this tool does not apply them.", ""])
    return "\n".join(lines)


def write_bundle(bundle: dict[str, object], output_dir: Path, output_format: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = str(bundle["bundle_id"])
    paths: list[Path] = []
    if output_format in {"json", "both"}:
        path = output_dir / f"{stem}.json"
        path.write_text(json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        paths.append(path)
    if output_format in {"markdown", "both"}:
        path = output_dir / f"{stem}.md"
        path.write_text(markdown_bundle(bundle), encoding="utf-8")
        paths.append(path)
    return paths


def _positive_float(value: str) -> float:
    parsed = float(value)
    if not 0 < parsed <= MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError(f"must be greater than 0 and at most {MAX_TIMEOUT_SECONDS}")
    return parsed


def _bounded_bytes(value: str) -> int:
    parsed = int(value)
    if not 256 <= parsed <= MAX_OUTPUT_BYTES:
        raise argparse.ArgumentTypeError(f"must be between 256 and {MAX_OUTPUT_BYTES}")
    return parsed


def parse_groups(value: str) -> list[str]:
    groups = [part.strip().lower() for part in value.split(",") if part.strip()]
    if not groups or ("all" in groups and len(groups) != 1) or any(group not in SOURCE_GROUPS and group != "all" for group in groups):
        raise argparse.ArgumentTypeError(f"choose comma-separated groups from: all, {', '.join(SOURCE_GROUPS)}")
    return list(SOURCE_GROUPS) if groups == ["all"] else list(dict.fromkeys(groups))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect a bounded, redacted, read-only incident evidence bundle.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    collect = subparsers.add_parser("collect", help="explicitly collect the fixed status sources")
    collect.add_argument("--include", default="all", type=parse_groups, help="groups: all, kubectl, flux, status")
    collect.add_argument("--format", choices=("json", "markdown", "both"), default="both")
    collect.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    collect.add_argument("--timeout", type=_positive_float, default=15.0, dest="timeout_seconds")
    collect.add_argument("--max-bytes", type=_bounded_bytes, default=262_144)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bundle = collect_bundle(args.include, args.timeout_seconds, args.max_bytes)
    for path in write_bundle(bundle, args.output_dir, args.format):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
