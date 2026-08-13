import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "incident_record.py"
spec = importlib.util.spec_from_file_location("incident_record", MODULE_PATH)
assert spec and spec.loader
incident_record = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = incident_record
spec.loader.exec_module(incident_record)


DECLARED_AT = "2026-08-10T15:00:00.000Z"


def new_record():
    return incident_record.empty_record(
        "TEST-INCIDENT-01",
        "Sanitized test incident",
        "SEV-3",
        DECLARED_AT,
        "ic-role",
        "ops-role",
        "comms-role",
        "planning-role",
    )


class IncidentRecordTests(unittest.TestCase):
    def test_start_record_has_roles_single_writer_and_safety_controls(self):
        record = new_record()
        incident_record.validate_record(record)
        self.assertEqual(record["record_control"]["single_writer_role"], "incident_commander")
        self.assertFalse(record["record_control"]["direct_cluster_mutation_allowed"])
        self.assertTrue(record["record_control"]["human_approval_required"])
        self.assertTrue(record["record_control"]["gitops_only_production_changes"])
        self.assertFalse(record["safety"]["raw_evidence_embedded"])
        self.assertEqual(record["timeline"][0]["at"], DECLARED_AT)

    def test_attach_bundle_copies_only_source_metadata_and_timestamps(self):
        record = new_record()
        bundle = {
            "bundle_id": "incident-20260810T150100000Z",
            "sources": [
                {
                    "id": "kubectl-pods",
                    "evidence_timestamp": "2026-08-10T15:01:00.000Z",
                    "status": "ok",
                    "truncated": False,
                    "stdout": '{"metadata":"must not be copied"}',
                },
                {
                    "id": "kubectl-events",
                    "evidence_timestamp": "2026-08-10T15:01:01.000Z",
                    "status": "timed_out",
                    "truncated": False,
                    "stderr": "private output must not be copied",
                },
            ],
        }
        additions = incident_record.attach_bundle(record, bundle)
        incident_record.validate_record(record)
        self.assertEqual(additions, 2)
        self.assertEqual(record["evidence"]["bundle_ids"], [bundle["bundle_id"]])
        self.assertEqual(
            [(item["source_id"], item["evidence_timestamp"], item["status"]) for item in record["evidence"]["sources"]],
            [("kubectl-pods", "2026-08-10T15:01:00.000Z", "ok"), ("kubectl-events", "2026-08-10T15:01:01.000Z", "timed_out")],
        )
        serialized = json.dumps(record)
        self.assertNotIn("must not be copied", serialized)
        self.assertNotIn("private output", serialized)
        self.assertTrue(set(record["timeline"][-1]["evidence_refs"]) == {"kubectl-pods", "kubectl-events"})

    def test_validation_fails_closed_for_sensitive_content_and_raw_output(self):
        for field, value in (
            ("title", "token: concrete-value"),
            ("title", "private telemetry 192.0.2.10"),
            ("title", "Bearer concrete-value"),
        ):
            record = new_record()
            record[field] = value
            with self.subTest(value=value), self.assertRaises(incident_record.RecordError):
                incident_record.validate_record(record)

        record = new_record()
        record["evidence"]["sources"].append({
            "source_id": "source-1",
            "evidence_timestamp": DECLARED_AT,
            "status": "ok",
            "completeness": "complete",
            "observation": "sanitized observation",
            "raw_output": "not permitted",
        })
        with self.assertRaises(incident_record.RecordError):
            incident_record.validate_record(record)

    def test_validation_requires_evidence_references_to_exist(self):
        record = new_record()
        record["timeline"].append({
            "at": DECLARED_AT,
            "event": "sanitized event",
            "actor_role": "operations_lead",
            "evidence_refs": ["missing-source"],
        })
        with self.assertRaises(incident_record.RecordError):
            incident_record.validate_record(record)

    def test_cli_start_writes_json_and_markdown_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable,
                str(MODULE_PATH),
                "start",
                "--id", "CLI-INCIDENT-01",
                "--title", "CLI sanitized incident",
                "--severity", "SEV-4",
                "--commander", "ic",
                "--declared-at", DECLARED_AT,
                "--output-dir", directory,
            ]
            first = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            json_path = Path(directory) / "incident-CLI-INCIDENT-01.json"
            markdown_path = Path(directory) / "incident-CLI-INCIDENT-01.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertIn("single writer", markdown_path.read_text(encoding="utf-8"))
            second = subprocess.run(command, text=True, capture_output=True, check=False)
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    unittest.main()
