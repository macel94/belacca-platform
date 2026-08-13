#!/usr/bin/env python3
"""Validate the platform SLO/error-budget policy without third-party packages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "docs" / "slo-policy.json"
EXPECTED_PUBLIC = {"portfolio", "pong", "analytics"}
EXPECTED_SERVICES = EXPECTED_PUBLIC | {"operator-surfaces"}
EXPECTED_STATES = {"normal-delivery", "caution-review", "reliability-first"}


class PolicyError(ValueError):
    """Raised when the policy is unsafe or structurally invalid."""


def fail(message: str) -> None:
    raise PolicyError(message)


def require_string(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        fail(f"{field} must be a non-empty string")


def require_keys(value: object, field: str, required: set[str], allowed: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        fail(f"{field} must be an object")
    actual = set(value)
    missing = required - actual
    if missing:
        fail(f"{field} missing fields: {', '.join(sorted(missing))}")
    if allowed is not None:
        unexpected = actual - allowed
        if unexpected:
            fail(f"{field} has unexpected fields: {', '.join(sorted(unexpected))}")
    return value


def validate_target(target: object) -> None:
    target = require_keys(target, "target", {
        "availability", "target_percent", "window", "window_hours",
        "observation_cadence", "error_budget_bad_slots", "claim_rule",
    })
    if target["availability"] != 0.99 or target["target_percent"] != "99%":
        fail("target must be 99%")
    if target["window"] != "rolling 30d" or target["window_hours"] != 720:
        fail("target window must be rolling 30d/720 hours")
    if target["observation_cadence"] != "1h" or target["error_budget_bad_slots"] != 7.2:
        fail("target cadence or 7.2-slot budget is invalid")
    require_string(target["claim_rule"], "target.claim_rule")


def validate_measurement(measurement: object) -> None:
    measurement = require_keys(measurement, "measurement", {
        "source_repository", "source_artifact", "source_history_schema", "source_kind",
        "attempt_policy", "denominator", "unknown_policy", "window_policy",
    })
    expected = {
        "source_repository": "macel94/belacca-status",
        "source_artifact": "slo.json",
        "source_history_schema": "belacca.observation.v1",
        "source_kind": "external-durable-synthetic-probe",
    }
    for field, value in expected.items():
        if measurement[field] != value:
            fail(f"measurement.{field} is not the durable external source contract")
    for field in ("attempt_policy", "denominator", "unknown_policy", "window_policy"):
        require_string(measurement[field], f"measurement.{field}")
    if "never count as good" not in measurement["unknown_policy"]:
        fail("unknown policy must not count unknown slots as good")
    if "coverage" not in measurement["unknown_policy"] or "cannot improve" not in measurement["unknown_policy"]:
        fail("unknown policy must preserve coverage context without improving the measured level")


def validate_service(service: object, index: int) -> None:
    service = require_keys(service, f"services[{index}]", {
        "id", "name", "scope", "slo_status", "target_percent", "window", "observation_cadence", "error_budget_bad_slots", "owner", "public_hosts", "measurement_source",
        "native_production_implementation", "journey", "numerator", "denominator",
        "good_observation", "bad_observation", "unknown_observation", "review_cadence", "runbook",
    }, {
        "id", "name", "scope", "slo_status", "target_percent", "window", "observation_cadence", "error_budget_bad_slots", "enabled", "owner", "public_hosts", "measurement_source",
        "native_production_implementation", "journey", "numerator", "denominator", "good_observation",
        "bad_observation", "unknown_observation", "activation_rule", "review_cadence", "runbook",
    })
    service_id = service["id"]
    if service_id not in EXPECTED_SERVICES:
        fail(f"unknown service id: {service_id}")
    for field in ("name", "owner", "native_production_implementation", "journey", "numerator", "denominator", "good_observation", "bad_observation", "unknown_observation", "review_cadence", "runbook"):
        require_string(service[field], f"services[{index}].{field}")
    if service["target_percent"] != "99%" or service["window"] != "rolling 30d" or service["observation_cadence"] != "1h" or service["error_budget_bad_slots"] != 7.2:
        fail(f"services[{index}] must explicitly carry the 99%/30d/hourly/7.2 policy")
    if service["owner"] != "platform":
        fail(f"services[{index}] owner must be platform")
    hosts = service["public_hosts"]
    if not isinstance(hosts, list) or not hosts or not all(isinstance(host, str) and host for host in hosts):
        fail(f"services[{index}].public_hosts must be non-empty strings")
    if service["native_production_implementation"].find("belacca-gitops") < 0:
        fail(f"services[{index}] must identify the live belacca-gitops implementation")
    if service["measurement_source"] is not None and "belacca-status" not in service["measurement_source"]:
        fail(f"services[{index}] measurement source must identify belacca-status")
    if service_id in EXPECTED_PUBLIC:
        if service["scope"] != "public" or service["slo_status"] != "proposed":
            fail(f"public service {service_id} must be a proposed public SLO")
        if service["measurement_source"] is None:
            fail(f"public service {service_id} needs a measurement source")
    else:
        if service["scope"] != "protected-operator" or service["slo_status"] != "not_configured":
            fail("operator surfaces must remain not_configured")
        if service.get("enabled") is not False or service["measurement_source"] is not None:
            fail("operator surfaces cannot be enabled without an authenticated source")
        require_string(service.get("activation_rule"), "operator-surfaces.activation_rule")
        if "Do not activate" not in service["activation_rule"]:
            fail("operator activation must be explicit and fail closed")


def validate_budget(policy: object) -> None:
    budget = require_keys(policy, "error_budget_policy", {"calculation", "states", "reentry"})
    for field in ("calculation", "reentry"):
        require_string(budget[field], f"error_budget_policy.{field}")
    if "7.2" not in budget["calculation"] or "unknown" not in budget["calculation"]:
        fail("error-budget calculation must state the 7.2 budget and unknown behavior")
    states = budget["states"]
    if not isinstance(states, list) or len(states) != 3:
        fail("error-budget policy must define exactly three decision states")
    names = set()
    for index, state in enumerate(states):
        state = require_keys(state, f"error_budget_policy.states[{index}]", {"state", "condition", "release_action"})
        names.add(state["state"])
        if state["state"] not in EXPECTED_STATES:
            fail(f"unknown error-budget state: {state['state']}")
        require_string(state["condition"], f"state[{index}].condition")
        require_string(state["release_action"], f"state[{index}].release_action")
    if names != EXPECTED_STATES:
        fail("error-budget states must be normal-delivery, caution-review, reliability-first")
    normal = next(item for item in states if item["state"] == "normal-delivery")
    caution = next(item for item in states if item["state"] == "caution-review")
    reliable = next(item for item in states if item["state"] == "reliability-first")
    if "3.6" not in normal["condition"] or "50%" not in normal["condition"]:
        fail("normal-delivery must use the half-budget threshold")
    if "3.6" not in caution["condition"] or "7.2" not in caution["condition"] or "unknown" not in caution["condition"]:
        fail("caution-review must cover half budget, full budget, and unknown data")
    if "7.2" not in reliable["condition"] or "active user-impacting incident" not in reliable["condition"]:
        fail("reliability-first must cover exhausted budget and active incidents")
    if "Pause" not in reliable["release_action"]:
        fail("reliability-first must pause non-emergency feature delivery")
    if "human" not in reliable["release_action"].lower():
        fail("reliability-first must retain human approval")


def validate_links(links: object) -> None:
    if not isinstance(links, list) or len(links) < 3:
        fail("implementation_links must include status, gitops, and Pong")
    repositories = set()
    for index, link in enumerate(links):
        link = require_keys(link, f"implementation_links[{index}]", {"repository", "issue", "purpose"})
        repositories.add(link["repository"])
        require_string(link["repository"], f"implementation_links[{index}].repository")
        require_string(link["purpose"], f"implementation_links[{index}].purpose")
        parsed = urlparse(link["issue"])
        if parsed.scheme != "https" or parsed.netloc != "github.com" or "/issues/" not in parsed.path:
            fail(f"implementation_links[{index}].issue must be a GitHub issue URL")
    required = {"macel94/belacca-status", "macel94/belacca-gitops", "macel94/cloudnativepong"}
    if not required <= repositories:
        fail("implementation links must cover all dependent repositories")


def validate_policy(policy: object) -> dict:
    policy = require_keys(policy, "policy", {
        "$schema", "schema_version", "policy_id", "status", "owner", "review_cadence", "target", "non_sla",
        "measurement", "services", "error_budget_policy", "evidence_boundaries", "implementation_links",
    })
    if policy["$schema"] != "./slo-policy.schema.json" or policy["schema_version"] != "belacca.slo-policy.v1":
        fail("unexpected policy schema")
    if policy["policy_id"] != "belacca-slo-99-v1" or policy["status"] != "approved-initial-policy" or policy["owner"] != "platform":
        fail("unexpected policy identity/status/owner")
    require_string(policy["review_cadence"], "review_cadence")
    require_string(policy["non_sla"], "non_sla")
    if "not an SLA" not in policy["non_sla"] or "service-credit" not in policy["non_sla"]:
        fail("non-SLA wording must exclude contractual credits")
    validate_target(policy["target"])
    validate_measurement(policy["measurement"])
    services = policy["services"]
    service_ids = [service.get("id") for service in services] if isinstance(services, list) else []
    if len(service_ids) != len(set(service_ids)) or set(service_ids) != EXPECTED_SERVICES:
        fail("policy must define portfolio, pong, analytics, and operator-surfaces exactly once")
    for index, service in enumerate(services):
        validate_service(service, index)
    boundaries = require_keys(policy["evidence_boundaries"], "evidence_boundaries", {"public_status", "slo_evidence", "paging", "privacy"})
    for field in boundaries:
        require_string(boundaries[field], f"evidence_boundaries.{field}")
    if "not an SLO" not in boundaries["public_status"] or "not a paging" not in boundaries["public_status"]:
        fail("public status boundary must distinguish SLO and paging")
    if "not an availability" not in boundaries["slo_evidence"] or "not a public uptime" not in boundaries["slo_evidence"]:
        fail("SLO evidence boundary must distinguish public claims")
    if "separate" not in boundaries["paging"] or "not claimed" not in boundaries["paging"]:
        fail("paging boundary must be separate and fail closed")
    validate_budget(policy["error_budget_policy"])
    validate_links(policy["implementation_links"])
    return policy


def load_policy(path: Path = POLICY_PATH) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            return validate_policy(json.load(handle))
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyError(str(error)) from error


def main() -> int:
    try:
        policy = load_policy(Path(sys.argv[1]) if len(sys.argv) > 1 else POLICY_PATH)
    except PolicyError as error:
        print(f"SLO policy validation failed: {error}", file=sys.stderr)
        return 1
    print(f"validated {len(policy['services'])} services in {POLICY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
