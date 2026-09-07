from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

DEPLOYMENTS = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


manage = module("deployment_manage", DEPLOYMENTS / "scripts/manage.py")
promotions = module("deployment_promotions", DEPLOYMENTS / "scripts/promote_images.py")


class RenderTests(unittest.TestCase):
    def test_all_environment_profile_combinations(self) -> None:
        environments = json.loads((DEPLOYMENTS / "config/environments.json").read_text())
        profiles = json.loads((DEPLOYMENTS / "config/profiles.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for environment in environments:
                for profile in profiles:
                    rendered = manage.render(environment, profile, output)
                    manage.validate_directory(rendered)
                    bundle = (rendered / "cml-memoryhive.yaml").read_text()
                    self.assertNotIn("kind: \"Secret\"", bundle)
                    self.assertNotRegex(bundle, r"\$\{[A-Z][A-Z0-9_]*\}")
                    if profile == "infra":
                        self.assertNotIn('kind: "Ingress"', bundle)
                        self.assertNotIn('name: "cml-memoryhive-backend"', bundle)
                        self.assertNotIn('"cml-memoryhive-backend"', bundle)
                        self.assertNotIn('"cml-memoryhive-frontend"', bundle)
                    if profile == "full":
                        self.assertIn('kind: "Ingress"', bundle)
                        self.assertIn('name: "cml-memoryhive-backend"', bundle)
                    if profiles[profile]["include_network_policies"]:
                        self.assertIn('kind: "NetworkPolicy"', bundle)

    def test_template_allowlist_rejects_unknown_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            old = manage.TEMPLATES
            try:
                manage.TEMPLATES = Path(temporary)
                (manage.TEMPLATES / "bad.tpl").write_text("${UNAPPROVED}\n")
                with self.assertRaises(ValueError):
                    manage.render_template("bad.tpl", {"UNAPPROVED": "x"}, {"APP"})
            finally:
                manage.TEMPLATES = old

    def test_nonlocal_secrets_reject_placeholders(self) -> None:
        profile = json.loads((DEPLOYMENTS / "config/profiles.json").read_text())["full"]
        with self.assertRaises(SystemExit):
            manage.secret_values("production", profile, DEPLOYMENTS / ".env.secrets.example")


class PromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pins = json.loads((DEPLOYMENTS / "image-versions.json").read_text())
        immutable_backend = "ghcr.io/coding-monkey-labs-client-projects/cml-memoryhive-backend:v2.0.0-abcdef0"
        immutable_frontend = "ghcr.io/coding-monkey-labs-client-projects/cml-memoryhive-frontend:v2.0.0-abcdef0"
        self.manifest = {
            "app": "cml-memoryhive",
            "runtime": {
                "cml-memoryhive-backend": immutable_backend,
                "cml-memoryhive-worker": immutable_backend,
                "cml-memoryhive-temporal-worker": immutable_backend,
                "cml-memoryhive-temporal-scheduler": immutable_backend,
                "cml-memoryhive-frontend": immutable_frontend,
            },
        }

    def test_staging_then_exact_production_promotion(self) -> None:
        self.assertTrue(promotions.promote("staging", self.pins, self.manifest))
        self.assertFalse(promotions.promote("staging", self.pins, self.manifest))
        self.assertTrue(promotions.promote("production", self.pins, None))
        for key in promotions.OWNED:
            self.assertEqual(self.pins["production"][key], self.pins["staging"][key])

    def test_rejects_floating_tags(self) -> None:
        self.manifest["runtime"]["cml-memoryhive-backend"] = "ghcr.io/coding-monkey-labs-client-projects/cml-memoryhive-backend:latest"
        with self.assertRaises(ValueError):
            promotions.promote("staging", self.pins, self.manifest)


if __name__ == "__main__":
    unittest.main()
