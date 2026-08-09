import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "incident-lifecycle.md"


class IncidentLifecycleDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = DOCUMENT.read_text(encoding="utf-8")

    def test_template_markers_and_required_sections_are_present(self):
        required = (
            "<!-- TEMPLATE:INCIDENT-STATE:START -->",
            "<!-- TEMPLATE:INCIDENT-STATE:END -->",
            "<!-- TEMPLATE:POSTMORTEM:START -->",
            "<!-- TEMPLATE:POSTMORTEM:END -->",
            "## Severity levels",
            "## Objective postmortem triggers",
            "## Roles and handoffs",
            "## Completed sanitized example (not a production incident)",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.document)

        incident_state = self.document.split(
            "<!-- TEMPLATE:INCIDENT-STATE:START -->", 1
        )[1].split("<!-- TEMPLATE:INCIDENT-STATE:END -->", 1)[0]
        postmortem = self.document.split(
            "<!-- TEMPLATE:POSTMORTEM:START -->", 1
        )[1].split("<!-- TEMPLATE:POSTMORTEM:END -->", 1)[0]
        for field in (
            "Incident Commander",
            "Operations Lead",
            "Communications Lead",
            "Planning/Follow-up Lead",
            "Current impact",
            "Timeline (UTC)",
            "Hypotheses and tests",
            "Change control",
            "Handoffs and communications",
            "Closure criteria",
        ):
            with self.subTest(template="incident state", field=field):
                self.assertIn(field, incident_state)
        for field in (
            "Impact",
            "Detection and response",
            "Timeline (UTC)",
            "Contributing factors and hypotheses",
            "What went well / poorly",
            "Recovery",
            "SLO and error-budget context",
            "Follow-ups",
            "Review and closure",
        ):
            with self.subTest(template="postmortem", field=field):
                self.assertIn(field, postmortem)

    def test_templates_and_example_enforce_safety_boundary(self):
        safety_terms = (
            "secrets",
            "player data",
            "tokens",
            "unredacted private telemetry",
            "no direct cluster mutation",
            "human-approved",
            "GitOps",
        )
        for term in safety_terms:
            with self.subTest(term=term):
                self.assertIn(term.lower(), self.document.lower())

        # A template may name a sensitive category, but must not contain a
        # concrete credential assignment or token-shaped value.
        self.assertNotRegex(
            self.document,
            r"(?i)(?:password|passwd|token|api[_-]?key|authorization)\s*[:=]\s*[^`\[({]",
        )
        self.assertNotRegex(
            self.document,
            r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b",
        )

    def test_evidence_linkage_and_example_limitations_are_explicit(self):
        self.assertRegex(self.document, r"source ID[s]?")
        self.assertRegex(self.document.lower(), r"evidence\s+timestamp[s]?")
        self.assertIn("Evidence source IDs + timestamps", self.document)
        self.assertIn("RUN-31286754660", self.document)
        self.assertIn("DOC-BASELINE-PLAN", self.document)
        self.assertIn("DOC-BASELINE-WORKFLOW", self.document)
        self.assertIn("not a chaos drill", self.document)
        self.assertIn("six-minute objective is **not proven**", self.document)
        self.assertIn("no production impact", self.document)
        self.assertIn("3/3 bounded journeys passed", self.document)

    def test_severity_and_objective_trigger_values_are_not_ambiguous(self):
        for level in ("SEV-1 Critical", "SEV-2 Major", "SEV-3 Moderate", "SEV-4 Minor / observation"):
            with self.subTest(level=level):
                self.assertIn(level, self.document)
        for trigger in (
            "User-facing critical failure",
            "Monitoring failure",
            "Data integrity or security event",
            "Recovery objective miss",
            "Repeat or noisy incident",
        ):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, self.document)
        self.assertRegex(self.document, r"99% availability over a rolling 30-day\s+window")
        self.assertIn("P95 recovery under 6 minutes", self.document)


if __name__ == "__main__":
    unittest.main()
