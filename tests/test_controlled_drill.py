import copy
import importlib.util
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_controlled_drill.py"
spec = importlib.util.spec_from_file_location("validate_controlled_drill", MODULE_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


class ControlledDrillValidatorTests(unittest.TestCase):
    @staticmethod
    def timestamp(seconds: int) -> str:
        return (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @classmethod
    def repetition(cls, index: int, duration: float, *, pong: bool = False, status: str = "pass", follow_up=None):
        start_seconds = index * 1000
        checks = [
            {
                "id": "health",
                "result": "pass",
                "observed_at": cls.timestamp(start_seconds + 1),
                "evidence_reference": f"EV-{index}-health",
                "exact_check": "GET private-isolated/health returned the documented success result",
            },
            {
                "id": "api-crud",
                "result": "pass",
                "observed_at": cls.timestamp(start_seconds + 2),
                "evidence_reference": f"EV-{index}-crud",
                "exact_check": "Synthetic list/create/update/delete operations returned documented success results",
            },
            {
                "id": "canonical-pong-two-player-journey",
                "result": "pass" if pong else "not_applicable",
                "observed_at": cls.timestamp(start_seconds + 3),
                "evidence_reference": f"EV-{index}-pong",
                "exact_check": "Two synthetic players completed the canonical WebSocket-compatible journey" if pong else "Pong journey does not apply to this isolated non-Pong service",
            },
            {
                "id": "cleanup",
                "result": "pass",
                "observed_at": cls.timestamp(start_seconds + int(duration)),
                "evidence_reference": f"EV-{index}-cleanup",
                "exact_check": "Synthetic resources and the approved fault were removed and post-drill health passed",
            },
        ]
        if not pong:
            checks[2]["not_applicable_reason"] = "This repetition targets the isolated portfolio service, not Pong."
        if status == "fail":
            checks[1]["result"] = "fail"
            checks[1]["exact_check"] = "Synthetic create operation did not return the documented success result"
        return {
            "id": f"drill-{index}",
            "comparability_key": "isolated-portfolio-restart-v1",
            "fault_class": "single-workload-restart",
            "start": {
                "kind": "fault_injection",
                "timestamp": cls.timestamp(start_seconds),
                "evidence_reference": f"EV-{index}-start",
            },
            "stop": {
                "timestamp": cls.timestamp(start_seconds + int(duration)),
                "evidence_reference": f"EV-{index}-stop",
            },
            "duration_seconds": duration,
            "recovery_status": status,
            "recovery_checks": checks,
            "impact": "No public endpoint targeted; isolated synthetic workload only.",
            "runbook_revision": "controlled-drill-recovery.md@v1",
            "follow_up_issue": follow_up,
        }

    @classmethod
    def record(cls, durations=(10, 20, 100), *, claimable=True):
        repetitions = [cls.repetition(index + 1, duration) for index, duration in enumerate(durations)]
        p95 = sorted(durations)[max(1, __import__("math").ceil(0.95 * len(durations))) - 1]
        return {
            "$schema": "https://raw.githubusercontent.com/macel94/belacca-platform/main/docs/controlled-drill-recovery.schema.json",
            "schema_version": "belacca.controlled-drill-evidence.v1",
            "sanitized": True,
            "record_type": "controlled_drill_batch",
            "objective": {
                "id": "belacca-controlled-drill-recovery-v1",
                "availability_slo": {
                    "target_percent": "99%",
                    "window": "rolling_30d",
                    "sla": False,
                    "separate_from_recovery_objective": True,
                },
                "recovery_target_seconds": 360,
                "percentile": "P95",
                "comparison": "strictly_under",
                "minimum_comparable_repetitions": 3,
            },
            "environment": {
                "scope": "isolated-capacity-chaos",
                "environment_reference": "isolated-runner-01",
                "production": False,
            },
            "safety": {
                "approved": True,
                "approval": {
                    "approver_role": "on-call operator",
                    "approved_at": cls.timestamp(0),
                    "change_reference": "CHANGE-123",
                },
                "bounded": {
                    "fault_scope": "one isolated portfolio workload restart",
                    "abort_conditions": ["unexpected public-route or cross-namespace traffic"],
                    "rollback_or_cleanup_plan": "isolated environment cleanup procedure v1",
                },
                "public_endpoint_targeted": False,
                "target_reference": "private://isolated-runner-01/portfolio",
                "mutation_performed": True,
            },
            "repetitions": repetitions,
            "evaluation": {
                "comparable_repetition_count": len(repetitions),
                "p95_method": "nearest_rank",
                "p95_duration_seconds": p95,
                "target_status": "pass" if claimable and p95 < 360 else "not_claimed",
                "claimable": claimable,
            },
            "limitations": ["Synthetic isolated evidence does not establish the public availability SLO."],
        }

    def assert_valid(self, record):
        self.assertEqual(validator.validate(record), [])

    def test_three_comparable_repetitions_produce_nearest_rank_p95(self):
        record = self.record((10, 20, 100))
        self.assert_valid(record)
        self.assertEqual(record["evaluation"]["p95_duration_seconds"], 100)

    def test_two_repetitions_are_valid_evidence_but_cannot_claim_p95(self):
        record = self.record((10, 20), claimable=False)
        self.assert_valid(record)
        self.assertFalse(record["evaluation"]["claimable"])
        self.assertEqual(record["evaluation"]["target_status"], "not_claimed")

    def test_duration_must_match_timestamps(self):
        record = self.record()
        record["repetitions"][0]["duration_seconds"] = 11
        errors = validator.validate(record)
        self.assertTrue(any("stop minus start" in error for error in errors), errors)

    def test_all_four_exact_recovery_checks_are_required(self):
        record = self.record()
        record["repetitions"][0]["recovery_checks"] = record["repetitions"][0]["recovery_checks"][:3]
        errors = validator.validate(record)
        self.assertTrue(any("exactly the four required checks" in error for error in errors), errors)

    def test_non_pong_check_requires_explicit_not_applicable_reason(self):
        record = self.record()
        del record["repetitions"][0]["recovery_checks"][2]["not_applicable_reason"]
        errors = validator.validate(record)
        self.assertTrue(any("not_applicable_reason" in error for error in errors), errors)

    def test_health_api_and_cleanup_cannot_be_not_applicable(self):
        record = self.record()
        record["repetitions"][0]["recovery_checks"][0]["result"] = "not_applicable"
        record["repetitions"][0]["recovery_checks"][0]["not_applicable_reason"] = "Not tested"
        errors = validator.validate(record)
        self.assertTrue(any("only the canonical Pong journey" in error for error in errors), errors)

    def test_recovery_check_must_be_observed_before_stop(self):
        record = self.record()
        record["repetitions"][0]["recovery_checks"][0]["observed_at"] = self.timestamp(9999)
        errors = validator.validate(record)
        self.assertTrue(any("after stop.timestamp" in error for error in errors), errors)

    def test_public_endpoint_is_rejected_even_when_approval_is_present(self):
        record = self.record()
        record["safety"]["target_reference"] = "https://pong.belacca.com"
        errors = validator.validate(record)
        self.assertTrue(any("live public endpoint" in error for error in errors), errors)

    def test_utc_timestamps_and_comparability_are_strict(self):
        malformed_timestamp = self.record()
        malformed_timestamp["repetitions"][0]["start"]["timestamp"] = "2026-01-01T00:00:00+00:00"
        errors = validator.validate(malformed_timestamp)
        self.assertTrue(any("UTC timestamp" in error for error in errors), errors)

        mixed_comparability = self.record()
        mixed_comparability["repetitions"][1]["comparability_key"] = "different-fault-v1"
        errors = validator.validate(mixed_comparability)
        self.assertTrue(any("comparability_key" in error for error in errors), errors)

    def test_target_is_strictly_under_360_seconds(self):
        passing = self.record((359, 359, 359))
        self.assert_valid(passing)
        failing = self.record((360, 360, 360))
        failing["evaluation"]["target_status"] = "fail"
        for repetition in failing["repetitions"]:
            repetition["follow_up_issue"] = "ISSUE-RECOVERY-FOLLOW-UP"
        self.assert_valid(failing)

    def test_failed_recovery_requires_follow_up_issue(self):
        record = self.record((10, 20, 30))
        record["repetitions"][0] = self.repetition(1, 30, status="fail")
        record["evaluation"]["p95_duration_seconds"] = 30
        record["evaluation"]["target_status"] = "pass"
        errors = validator.validate(record)
        self.assertTrue(any("follow_up_issue" in error for error in errors), errors)

    def test_schema_and_runbook_state_separate_objectives_and_limitations(self):
        schema = json.loads((ROOT / "docs" / "controlled-drill-recovery.schema.json").read_text())
        self.assertEqual(schema["properties"]["objective"]["properties"]["recovery_target_seconds"]["const"], 360)
        runbook = (ROOT / "docs" / "controlled-drill-recovery.md").read_text()
        for phrase in (
            "99% per supported public application over a rolling 30-day window",
            "strictly under 360 seconds",
            "at least three comparable repetitions",
            "Do not target the live public endpoint by default",
            "follow-up issue/postmortem",
        ):
            self.assertIn(phrase, runbook)


if __name__ == "__main__":
    unittest.main()
