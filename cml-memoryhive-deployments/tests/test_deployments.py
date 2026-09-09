from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

DEPLOYMENTS = Path(__file__).resolve().parents[1]
REPO_ROOT = DEPLOYMENTS.parent


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
    def test_project_makefile_exposes_supported_command_surface(self) -> None:
        makefile = (DEPLOYMENTS / "Makefile").read_text()
        for target in (
            "generate",
            "validate",
            "validate-all",
            "readiness-all",
            "apply",
            "upgrade",
            "status",
            "rollback",
            "delete",
            "test",
        ):
            self.assertRegex(makefile, rf"(?m)^{target}\s*:[^\n]*$")

    def test_all_environment_profile_combinations(self) -> None:
        environments = json.loads(
            (DEPLOYMENTS / "config/environments.json").read_text()
        )
        profiles = json.loads((DEPLOYMENTS / "config/profiles.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for environment in environments:
                for profile in profiles:
                    rendered = manage.render(environment, profile, output)
                    manage.validate_directory(rendered)
                    bundle = (rendered / "cml-memoryhive.yaml").read_text()
                    documents = list(yaml.safe_load_all(bundle))
                    kinds = {document["kind"] for document in documents}
                    names = {document["metadata"]["name"] for document in documents}
                    self.assertNotIn("Secret", kinds)
                    self.assertNotRegex(bundle, r"\$\{[A-Z][A-Z0-9_]*\}")
                    if profile == "infra":
                        self.assertNotIn("Ingress", kinds)
                        self.assertNotIn("cml-memoryhive-backend", names)
                        self.assertNotIn('"cml-memoryhive-backend"', bundle)
                        self.assertNotIn('"cml-memoryhive-frontend"', bundle)
                    if profile == "full":
                        self.assertIn("Ingress", kinds)
                        self.assertIn("cml-memoryhive-backend", names)
                    if profiles[profile]["include_network_policies"]:
                        self.assertIn("NetworkPolicy", kinds)

    def test_production_uses_canonical_public_origin_and_api_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            rendered = manage.render("production", "full", Path(temporary))
            documents = list(
                yaml.safe_load_all((rendered / "cml-memoryhive.yaml").read_text())
            )

        ingress = next(document for document in documents if document["kind"] == "Ingress")
        rule = ingress["spec"]["rules"][0]
        self.assertEqual(rule["host"], "www.memoryhive.in")
        self.assertEqual(ingress["spec"]["tls"][0]["hosts"], ["www.memoryhive.in"])
        routes = {
            route["path"]: route["backend"]["service"]["name"]
            for route in rule["http"]["paths"]
        }
        self.assertEqual(routes["/api/v1"], "cml-memoryhive-backend")
        self.assertEqual(routes["/"], "cml-memoryhive-frontend")

        backend_config = next(
            document
            for document in documents
            if document["kind"] == "ConfigMap"
            and document["metadata"]["name"] == "cml-memoryhive-backend-config"
        )
        self.assertEqual(
            backend_config["data"]["CORS_ORIGINS"],
            '["https://www.memoryhive.in"]',
        )
        self.assertEqual(
            backend_config["data"]["ALLOWED_HOSTS"], '["www.memoryhive.in"]'
        )

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

    def test_every_supported_resource_kind_has_a_readable_template(self) -> None:
        self.assertEqual(
            set(manage.RESOURCE_TEMPLATES),
            {
                "ConfigMap",
                "Deployment",
                "Ingress",
                "LimitRange",
                "Namespace",
                "NetworkPolicy",
                "ResourceQuota",
                "Secret",
                "Service",
                "ServiceAccount",
                "StatefulSet",
            },
        )
        for template in manage.RESOURCE_TEMPLATES.values():
            contents = (manage.TEMPLATES / template).read_text()
            self.assertIn("apiVersion: ${API_VERSION}", contents)
            self.assertIn("metadata:", contents)
            self.assertNotIn("${SPEC}", contents)
        visible_fields = {
            "Deployment": ("replicas:", "selector:", "template:"),
            "StatefulSet": ("serviceName:", "volumeClaimTemplates:"),
            "Service": ("type:", "ports:"),
            "Ingress": ("ingressClassName:", "tls:", "rules:"),
            "NetworkPolicy": ("podSelector:", "policyTypes:"),
            "ResourceQuota": ("hard:",),
            "LimitRange": ("limits:",),
        }
        for kind, fields in visible_fields.items():
            contents = (manage.TEMPLATES / manage.RESOURCE_TEMPLATES[kind]).read_text()
            for field in fields:
                self.assertIn(field, contents)

    def test_resource_template_rejects_unrepresented_spec_fields(self) -> None:
        resource = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "test"},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": "test"}},
                "template": {
                    "metadata": {"labels": {"app": "test"}},
                    "spec": {"containers": [{"name": "test", "image": "test"}]},
                },
                "strategy": {},
            },
        }
        with self.assertRaisesRegex(ValueError, "does not cover spec fields"):
            manage.render_resource(resource)

    def test_committed_manifests_are_deterministic(self) -> None:
        environments = json.loads(
            (DEPLOYMENTS / "config/environments.json").read_text()
        )
        profiles = json.loads((DEPLOYMENTS / "config/profiles.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for environment in environments:
                for profile in profiles:
                    rendered = manage.render(environment, profile, output)
                    expected = (
                        DEPLOYMENTS
                        / "generated"
                        / environment
                        / profile
                        / "cml-memoryhive.yaml"
                    )
                    self.assertEqual(
                        (rendered / "cml-memoryhive.yaml").read_text(),
                        expected.read_text(),
                    )

    def test_deployments_use_only_environment_image_pins(self) -> None:
        pins = json.loads((DEPLOYMENTS / "image-versions.json").read_text())
        for environment, environment_pins in pins.items():
            for manifest in sorted(
                (DEPLOYMENTS / "generated" / environment).glob("*/cml-memoryhive.yaml")
            ):
                for document in yaml.safe_load_all(manifest.read_text()):
                    if document["kind"] != "Deployment":
                        continue
                    name = document["metadata"]["name"]
                    container = document["spec"]["template"]["spec"]["containers"][0]
                    if name.startswith("cml-memoryhive-"):
                        self.assertEqual(container["image"], environment_pins[name])
                    for init_container in document["spec"]["template"]["spec"].get(
                        "initContainers", []
                    ):
                        if init_container["name"] == "migrate":
                            self.assertEqual(
                                init_container["image"],
                                environment_pins["cml-memoryhive-backend"],
                            )

    def test_rendered_workloads_satisfy_resource_contracts(self) -> None:
        environments = json.loads(
            (DEPLOYMENTS / "config/environments.json").read_text()
        )
        profiles = json.loads((DEPLOYMENTS / "config/profiles.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for environment_name, environment in environments.items():
                for profile_name, profile in profiles.items():
                    rendered = manage.render(environment_name, profile_name, output)
                    documents = list(
                        yaml.safe_load_all(
                            (rendered / "cml-memoryhive.yaml").read_text()
                        )
                    )
                    config_maps = {
                        item["metadata"]["name"]
                        for item in documents
                        if item["kind"] == "ConfigMap"
                    }
                    service_accounts = {
                        item["metadata"]["name"]
                        for item in documents
                        if item["kind"] == "ServiceAccount"
                    }
                    workloads = {
                        item["metadata"]["name"]: item
                        for item in documents
                        if item["kind"] in {"Deployment", "StatefulSet"}
                    }
                    for item in documents:
                        component = (
                            item["metadata"]
                            .get("labels", {})
                            .get("app.kubernetes.io/component", "")
                        )
                        if component.startswith("cml-memoryhive-"):
                            self.assertTrue(
                                item["metadata"]["name"].startswith("cml-memoryhive-")
                            )
                        if item["kind"] == "Service":
                            target = workloads[item["metadata"]["name"]]
                            self.assertEqual(
                                item["spec"]["selector"],
                                target["spec"]["template"]["metadata"]["labels"],
                            )
                    for name in profile["services"]:
                        if not name.startswith("cml-memoryhive-"):
                            continue
                        workload = workloads[name]
                        pod = workload["spec"]["template"]["spec"]
                        container = pod["containers"][0]
                        self.assertEqual(
                            workload["spec"]["replicas"],
                            environment["replicas"][name],
                        )
                        self.assertIn(pod["serviceAccountName"], service_accounts)
                        self.assertFalse(pod["automountServiceAccountToken"])
                        self.assertEqual(
                            container["resources"], environment["resources"][name]
                        )
                        references = container["envFrom"]
                        self.assertIn(
                            {"configMapRef": {"name": f"{name}-config"}},
                            references,
                        )
                        self.assertIn(f"{name}-config", config_maps)
                        self.assertIn(
                            {"secretRef": {"name": f"{name}-secrets"}}, references
                        )
                        self.assertTrue(
                            "readinessProbe" in container
                            or "livenessProbe" in container
                        )
                        if name == "cml-memoryhive-backend":
                            migration = pod["initContainers"][0]
                            self.assertEqual(migration["name"], "migrate")
                            self.assertEqual(
                                migration["command"][:4],
                                ["uv", "run", "--frozen", "--no-sync"],
                            )
                    for item in workloads.values():
                        if item["kind"] == "StatefulSet":
                            self.assertTrue(item["spec"]["volumeClaimTemplates"])

    @unittest.skipUnless(shutil.which("kubectl"), "kubectl is not installed")
    def test_all_committed_manifests_pass_kubectl_client_dry_run(self) -> None:
        manifests = sorted((DEPLOYMENTS / "generated").glob("*/*/cml-memoryhive.yaml"))
        self.assertEqual(len(manifests), 12)
        for manifest in manifests:
            result = subprocess.run(
                [
                    "kubectl",
                    "apply",
                    "--dry-run=client",
                    "--validate=false",
                    "-f",
                    str(manifest),
                ],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"{manifest}: {result.stderr}")

    def test_nonlocal_secrets_reject_placeholders(self) -> None:
        profile = json.loads((DEPLOYMENTS / "config/profiles.json").read_text())["full"]
        with self.assertRaises(SystemExit):
            manage.secret_values(
                "production", profile, DEPLOYMENTS / ".env.secrets.example"
            )

    def test_secrets_are_streamed_to_kubectl_without_a_file(self) -> None:
        env, profile, _images = manage.load_context("local", "app-only")
        with patch.object(manage.subprocess, "run") as run:
            manage.apply_secrets("local", env, profile, None)
        command = run.call_args.args[0]
        self.assertEqual(command[-3:], ["apply", "-f", "-"])
        self.assertIn("kind: Secret", run.call_args.kwargs["input"])
        self.assertTrue(run.call_args.kwargs["check"])

    def test_ingress_and_network_flags_materially_change_output(self) -> None:
        env, profile, images = manage.load_context("local", "full")
        disabled = {
            **profile,
            "include_ingress": False,
            "include_network_policies": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(
                manage, "load_context", return_value=(env, disabled, images)
            ):
                rendered = manage.render("local", "full", Path(temporary))
            kinds = {
                document["kind"]
                for document in yaml.safe_load_all(
                    (rendered / "cml-memoryhive.yaml").read_text()
                )
            }
        self.assertNotIn("Ingress", kinds)
        self.assertNotIn("NetworkPolicy", kinds)

    def test_nonlocal_cluster_mutations_reject_review_placeholders(self) -> None:
        env, profile, images = manage.load_context("production", "full")
        with self.assertRaisesRegex(SystemExit, "not deployment-ready"):
            manage.require_deployment_ready("production", env, profile, images)

    def test_validate_deployment_ready_is_a_strict_release_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local = manage.parser().parse_args(
                [
                    "--output",
                    temporary,
                    "validate",
                    "local",
                    "full",
                    "--deployment-ready",
                ]
            )
            self.assertEqual(manage.cmd_validate(local), 0)
            production = manage.parser().parse_args(
                [
                    "--output",
                    temporary,
                    "validate",
                    "production",
                    "full",
                    "--deployment-ready",
                ]
            )
            with self.assertRaisesRegex(SystemExit, "not deployment-ready"):
                manage.cmd_validate(production)

    def test_context_match_is_exact(self) -> None:
        environment = {"expected_context": "cml-memoryhive-production"}
        with patch.object(manage, "current_context", return_value="production"):
            with self.assertRaisesRegex(SystemExit, "Refusing cluster mutation"):
                manage.require_context(environment)

    def test_context_check_has_no_cli_bypass(self) -> None:
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            manage.parser().parse_args(
                ["apply", "local", "full", "--skip-context-check"]
            )

    def test_apply_creates_namespace_before_streaming_secrets(self) -> None:
        args = SimpleNamespace(
            environment="local",
            profile="app-only",
            output=Path(tempfile.mkdtemp()),
            secret_env_file=None,
        )
        self.addCleanup(shutil.rmtree, args.output)
        order: list[str] = []
        with (
            patch.object(manage, "require_context"),
            patch.object(
                manage,
                "apply_namespace",
                side_effect=lambda _env: order.append("namespace"),
            ),
            patch.object(
                manage,
                "apply_secrets",
                side_effect=lambda *_args: order.append("secrets"),
            ),
            patch.object(
                manage, "kubectl", side_effect=lambda *_args: order.append("manifest")
            ),
        ):
            self.assertEqual(manage.cmd_apply(args), 0)
        self.assertEqual(order, ["namespace", "secrets", "manifest"])

    def test_upgrade_waits_only_for_changed_workloads(self) -> None:
        env, profile, images = manage.load_context("local", "app-only")
        current = {
            "cml-memoryhive-backend": images["cml-memoryhive-backend"],
            "cml-memoryhive-worker": None,
            "cml-memoryhive-frontend": None,
        }
        args = SimpleNamespace(
            environment="local",
            profile="app-only",
            skip_context_check=True,
            output=Path(tempfile.mkdtemp()),
            secret_env_file=None,
            timeout="5s",
        )
        self.addCleanup(shutil.rmtree, args.output)
        with (
            patch.object(manage, "require_context"),
            patch.object(manage, "apply_namespace"),
            patch.object(manage, "apply_secrets"),
            patch.object(manage, "apply_resources") as apply_resources,
            patch.object(
                manage, "deployment_image", side_effect=lambda _ns, name: current[name]
            ),
            patch.object(manage, "kubectl") as kubectl,
        ):
            self.assertEqual(manage.cmd_upgrade(args), 0)
        rollout_targets = [
            call.args[4]
            for call in kubectl.call_args_list
            if len(call.args) > 4 and call.args[2:4] == ("rollout", "status")
        ]
        self.assertEqual(
            rollout_targets,
            [
                "deployment/cml-memoryhive-worker",
                "deployment/cml-memoryhive-frontend",
            ],
        )
        applied_names = {
            resource["metadata"]["name"]
            for resource in apply_resources.call_args.args[0]
        }
        self.assertEqual(
            applied_names,
            {"cml-memoryhive-worker", "cml-memoryhive-frontend"},
        )

    def test_upgrade_is_a_true_no_op_when_all_pins_match(self) -> None:
        env, profile, images = manage.load_context("local", "app-only")
        args = SimpleNamespace(
            environment="local",
            profile="app-only",
            output=Path(tempfile.mkdtemp()),
            secret_env_file=None,
            timeout="5s",
        )
        self.addCleanup(shutil.rmtree, args.output)
        with (
            patch.object(manage, "require_context"),
            patch.object(
                manage,
                "deployment_image",
                side_effect=lambda _namespace, name: images[name],
            ),
            patch.object(manage, "apply_namespace") as apply_namespace,
            patch.object(manage, "apply_secrets") as apply_secrets,
            patch.object(manage, "apply_resources") as apply_resources,
            patch.object(manage, "kubectl") as kubectl,
        ):
            self.assertEqual(manage.cmd_upgrade(args), 0)
        apply_namespace.assert_not_called()
        apply_secrets.assert_not_called()
        apply_resources.assert_not_called()
        kubectl.assert_not_called()


class PromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pins = json.loads((DEPLOYMENTS / "image-versions.json").read_text())
        immutable_backend = "docker.io/maheshk172/cml-memoryhive-backend:v2.0.0-abcdef0"
        immutable_frontend = "docker.io/maheshk172/cml-memoryhive-frontend:v2.0.0-abcdef0"
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
        local_before = dict(self.pins["local"])
        production_before = dict(self.pins["production"])
        self.assertTrue(promotions.promote("staging", self.pins, self.manifest))
        self.assertEqual(self.pins["local"], local_before)
        self.assertEqual(self.pins["production"], production_before)
        self.assertFalse(promotions.promote("staging", self.pins, self.manifest))
        self.assertTrue(promotions.promote("production", self.pins, None))
        for key in promotions.OWNED:
            self.assertEqual(self.pins["production"][key], self.pins["staging"][key])

    def test_rejects_floating_tags(self) -> None:
        self.manifest["runtime"][
            "cml-memoryhive-backend"
        ] = "docker.io/maheshk172/cml-memoryhive-backend:latest"
        with self.assertRaises(ValueError):
            promotions.promote("staging", self.pins, self.manifest)

    def test_rejects_all_zero_placeholder_sha(self) -> None:
        self.manifest["runtime"][
            "cml-memoryhive-backend"
        ] = "docker.io/maheshk172/cml-memoryhive-backend:v0.0.0-0000000"
        with self.assertRaises(ValueError):
            promotions.promote("staging", self.pins, self.manifest)


class WorkflowContractTests(unittest.TestCase):
    def test_release_builds_from_registry_and_opens_staging_pr(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("cml-memoryhive-build/build/scripts/build_images.py", workflow)
        self.assertIn("promote_images.py staging", workflow)
        self.assertIn("peter-evans/create-pull-request", workflow)
        self.assertIn("base: main", workflow)
        self.assertIn("cml-memoryhive-deployments/generated/staging/**", workflow)
        self.assertIn("--deployment-ready", workflow)
        self.assertNotIn("git push", workflow)

    def test_production_promotion_is_manual_protected_and_pr_only(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/promote-production.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("environment: production", workflow)
        self.assertIn("promote_images.py production", workflow)
        self.assertIn("peter-evans/create-pull-request", workflow)
        self.assertIn("base: main", workflow)
        self.assertIn("cml-memoryhive-deployments/generated/production/**", workflow)
        self.assertIn("--deployment-ready", workflow)
        self.assertNotIn("git push", workflow)

    def test_deployment_workflow_uses_cli_and_environment_gate(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/k8s-deploy.yml").read_text()
        self.assertIn("environment: ${{ inputs.environment }}", workflow)
        self.assertIn("cml-memoryhive-deployments/scripts/manage.py", workflow)
        self.assertIn("--kubectl-dry-run", workflow)


if __name__ == "__main__":
    unittest.main()
