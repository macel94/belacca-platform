#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "incident_evidence.py"
spec = importlib.util.spec_from_file_location("incident_evidence", MODULE_PATH)
assert spec and spec.loader
incident_evidence = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = incident_evidence
spec.loader.exec_module(incident_evidence)


class EvidenceToolTests(unittest.TestCase):
    def test_redaction_removes_secret_token_password_and_ip_like_values(self):
        payload = {
            "kind": "Secret",
            "data": {"password": "c2VjcmV0", "token": "eyJhbGciOiJIUzI1NiJ9.secret.signature"},
            "message": "Bearer top-secret 192.168.10.42 and 2001:db8::7",
            "config": {"password": "another-secret", "api_key": "key-value"},
        }
        output, counts, output_format = incident_evidence.sanitize_output(json.dumps(payload))
        self.assertEqual(output_format, "json")
        self.assertNotIn("c2VjcmV0", output)
        self.assertNotIn("top-secret", output)
        self.assertNotIn("another-secret", output)
        self.assertNotIn("key-value", output)
        self.assertNotIn("192.168.10.42", output)
        self.assertNotIn("2001:db8::7", output)
        self.assertIn("[REDACTED]", output)
        self.assertGreaterEqual(counts.get("secret", 0), 3)
        self.assertGreaterEqual(counts.get("ip", 0), 2)

    def test_collection_safe_failure_emits_evidence_and_no_action(self):
        def unavailable_runner(command, timeout_seconds, max_bytes):
            return incident_evidence.CommandResult(
                None,
                "",
                f"{command[0]} unavailable at 10.0.0.7",
                "unavailable",
            )

        bundle = incident_evidence.collect_bundle(
            ["kubectl", "flux"],
            runner=unavailable_runner,
        )
        self.assertTrue(bundle["read_only"])
        self.assertFalse(bundle["cluster_mutation_attempted"])
        self.assertEqual(len(bundle["sources"]), 5)
        self.assertTrue(all(source["status"] == "unavailable" for source in bundle["sources"]))
        self.assertTrue(all(source["stdout"] == "" for source in bundle["sources"]))
        self.assertTrue(all("10.0.0.7" not in source["stderr"] for source in bundle["sources"]))
        self.assertTrue(all(action["status"] == "pending_human_approval" for action in bundle["human_approved_actions"]))
        self.assertTrue(bundle["hypotheses"][1]["evidence_refs"])

    def test_timeout_is_recorded_and_mutating_commands_are_not_allowlisted(self):
        result = incident_evidence.run_bounded(
            (sys.executable, '-c', 'import time; time.sleep(2)'),
            timeout_seconds=0.05,
            max_bytes=1024,
        )
        self.assertEqual(result.status, 'timed_out')
        self.assertTrue(result.timed_out)
        self.assertFalse(incident_evidence._safe_command(('kubectl', 'apply', '-f', '-')))
        self.assertFalse(incident_evidence._safe_command(('kubectl', 'get', 'secrets', '--all-namespaces')))
        self.assertFalse(incident_evidence._safe_command(('kubectl', 'get', 'secret/site-token')))
        self.assertFalse(incident_evidence._safe_command(('flux', 'reconcile', 'kustomization', 'site')))

    def test_write_bundle_produces_json_and_markdown(self):
        bundle = incident_evidence.collect_bundle([], runner=lambda *_: None)
        with tempfile.TemporaryDirectory() as directory:
            paths = incident_evidence.write_bundle(bundle, Path(directory), "both")
            self.assertEqual({path.suffix for path in paths}, {".json", ".md"})
            saved = json.loads(next(path.read_text() for path in paths if path.suffix == ".json"))
            markdown = next(path.read_text() for path in paths if path.suffix == ".md")
            self.assertEqual(saved["schema_version"], "belacca.incident-evidence.v1")
            self.assertIn("Human-approved actions", markdown)
            self.assertIn("AI-assistance boundary", markdown)


if __name__ == "__main__":
    unittest.main()
