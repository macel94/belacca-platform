import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_slo_policy.py"
spec = importlib.util.spec_from_file_location("validate_slo_policy", MODULE_PATH)
assert spec and spec.loader
policy_validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy_validator
spec.loader.exec_module(policy_validator)


class SloPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "docs" / "slo-policy.json").read_text(encoding="utf-8"))

    def test_checked_in_policy_is_valid(self):
        validated = policy_validator.validate_policy(copy.deepcopy(self.policy))
        self.assertEqual(
            {service["id"] for service in validated["services"]},
            {"portfolio", "pong", "analytics", "operator-surfaces"},
        )

    def test_public_services_have_explicit_99_percent_measurements(self):
        for service in self.policy["services"]:
            if service["id"] == "operator-surfaces":
                continue
            self.assertEqual(service["scope"], "public")
            self.assertEqual(service["slo_status"], "proposed")
            self.assertIn("720", service["denominator"])
            self.assertTrue(service["numerator"])
            self.assertTrue(service["good_observation"])
            self.assertTrue(service["bad_observation"])
            self.assertTrue(service["unknown_observation"])

    def test_duplicate_service_ids_fail_closed(self):
        broken = copy.deepcopy(self.policy)
        broken["services"][1]["id"] = broken["services"][0]["id"]
        with self.assertRaises(policy_validator.PolicyError):
            policy_validator.validate_policy(broken)

    def test_unknown_data_and_operator_surface_fail_closed(self):
        broken = copy.deepcopy(self.policy)
        broken["measurement"]["unknown_policy"] = "Missing data is good."
        with self.assertRaises(policy_validator.PolicyError):
            policy_validator.validate_policy(broken)

        broken = copy.deepcopy(self.policy)
        operator = next(item for item in broken["services"] if item["id"] == "operator-surfaces")
        operator["enabled"] = True
        with self.assertRaises(policy_validator.PolicyError):
            policy_validator.validate_policy(broken)

    def test_error_budget_states_and_issue_links_are_complete(self):
        states = {item["state"] for item in self.policy["error_budget_policy"]["states"]}
        self.assertEqual(states, {"normal-delivery", "caution-review", "reliability-first"})
        repositories = {item["repository"] for item in self.policy["implementation_links"]}
        self.assertTrue({"macel94/belacca-status", "macel94/belacca-gitops", "macel94/cloudnativepong"} <= repositories)


if __name__ == "__main__":
    unittest.main()
