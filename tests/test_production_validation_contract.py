import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductionValidationContractTests(unittest.TestCase):
    def test_make_manifests_has_an_explicit_native_matrix(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        required = (
            "NATIVE_PRODUCTION_SOURCE",
            "NATIVE_PONG_SOURCE ?= cloudnativepong/k8s/overlays/native-staging",
            "NATIVE_SITE_SOURCE ?= francesco-belacca-site/deploy",
            "$(NATIVE_PRODUCTION_SOURCE)/flux-system",
            "$(NATIVE_PRODUCTION_SOURCE)/secrets",
            "$(NATIVE_PRODUCTION_SOURCE)/longhorn",
            "$(NATIVE_PRODUCTION_SOURCE)/edge",
            "$(NATIVE_PRODUCTION_SOURCE)/cert-manager",
            "$(NATIVE_PRODUCTION_SOURCE)/tls",
            "$(NATIVE_PRODUCTION_SOURCE)/routing",
            "$(NATIVE_PRODUCTION_SOURCE)/dex",
            "$(NATIVE_PRODUCTION_SOURCE)/analytics",
            "$(NATIVE_PRODUCTION_SOURCE)/observability",
            "$(NATIVE_PRODUCTION_SOURCE)/headlamp",
            "$(NATIVE_PRODUCTION_SOURCE)/flux-web",
            "kubectl kustomize \"$$path\"",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, makefile)

        manifests_body = makefile.split("manifests:\n", 1)[1].split(
            "# Explicit audit-only", 1
        )[0]
        self.assertNotIn("HISTORICAL_PRODUCTION_SOURCE", manifests_body)
        self.assertNotIn("overlays/server", manifests_body)

    def test_live_flux_and_application_paths_are_native_production(self):
        flux = (
            ROOT / "belacca-gitops/clusters/belacca-production/native-applications.yaml"
        ).read_text(encoding="utf-8")
        catalog = (ROOT / "belacca-gitops/catalog/services.json").read_text(
            encoding="utf-8"
        )
        self.assertIn("path: ./k8s/overlays/native-staging", flux)
        self.assertIn("native production target", catalog)
        self.assertNotIn("vmi3474918", catalog)
        self.assertIn('"cluster": "belacca-native"', catalog)

    def test_native_application_overlay_is_renderable_and_retired_tree_is_absent(self):
        native = ROOT / "cloudnativepong/k8s/overlays/native-staging"
        self.assertTrue((native / "kustomization.yaml").is_file())
        self.assertTrue((native / "api-native-staging.yaml").is_file())
        self.assertFalse(any((ROOT / "belacca-gitops/clusters").glob("*/HISTORICAL-REFERENCE.md")))


if __name__ == "__main__":
    unittest.main()
