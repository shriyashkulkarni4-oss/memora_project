from __future__ import annotations

import importlib.util
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

BUILD_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILD_ROOT.parent


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


build_images = module("build_images", BUILD_ROOT / "build/scripts/build_images.py")
image_manifest = module(
    "image_manifest", BUILD_ROOT / "build/scripts/generate_image_manifest.py"
)
runtime_generator = module(
    "runtime_generator", BUILD_ROOT / "scripts/generate_runtime.py"
)
check_ports = module("check_ports", BUILD_ROOT / "scripts/check_ports.py")
local_manager = module("local_manager", BUILD_ROOT / "runtime/manage_services_local.py")
health_check = module("health_check", BUILD_ROOT / "health_checker/health_check.py")


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads((BUILD_ROOT / "service-registry.json").read_text())

    def test_registry_integrity(self) -> None:
        self.assertEqual(self.registry["schema_version"], 1)
        self.assertEqual(self.registry["app"], "cml-memoryhive")
        self.assertEqual(
            set(self.registry["profiles"]), {"infra", "app-only", "full", "temporal"}
        )
        services = self.registry["services"]
        keys = [item["key"] for item in services]
        self.assertEqual(len(keys), len(set(keys)))
        images = {item["key"] for item in self.registry["images"]}
        self.assertEqual(images, {"cml-memoryhive-backend", "cml-memoryhive-frontend"})
        host_ports = [item["host_port"] for item in services if item.get("host_port")]
        host_ports.extend(
            port["host_port"]
            for item in services
            for port in item.get("additional_ports", [])
        )
        self.assertEqual(len(host_ports), len(set(host_ports)))
        for profile, members in self.registry["profiles"].items():
            self.assertTrue(members, profile)
            self.assertFalse(set(members) - set(keys), profile)
        for service in services:
            self.assertIn(service["health"]["type"], {"http", "tcp", "process"})
            self.assertFalse(set(service["depends_on"]) - set(keys), service["key"])
            if service.get("image_key"):
                self.assertIn(service["image_key"], images)
            if service.get("kubernetes"):
                self.assertIn(
                    service["kubernetes"]["kind"], {"deployment", "statefulset"}
                )
                self.assertTrue(service["kubernetes"]["name"])

    def test_dependency_graph_is_acyclic(self) -> None:
        graph = {
            item["key"]: set(item["depends_on"]) for item in self.registry["services"]
        }
        while graph:
            ready = {
                key
                for key, dependencies in graph.items()
                if not dependencies & graph.keys()
            }
            self.assertTrue(ready, f"dependency cycle: {graph}")
            graph = {
                key: dependencies - ready
                for key, dependencies in graph.items()
                if key not in ready
            }

    def test_all_dockerfiles_exist(self) -> None:
        for image in self.registry["images"]:
            self.assertTrue(
                (REPO_ROOT / image["context"] / image["dockerfile"]).is_file()
            )

    def test_runtime_schema_validation_rejects_invalid_registry_data(self) -> None:
        mutations = {}

        missing_health = copy.deepcopy(self.registry)
        del missing_health["services"][0]["health"]
        mutations["missing service field"] = missing_health

        duplicate_port = copy.deepcopy(self.registry)
        duplicate_port["services"][1]["host_port"] = duplicate_port["services"][0][
            "host_port"
        ]
        mutations["duplicate host port"] = duplicate_port

        unknown_image = copy.deepcopy(self.registry)
        unknown_image["services"][-1]["image_key"] = "missing-image"
        mutations["unknown image"] = unknown_image

        cycle = copy.deepcopy(self.registry)
        cycle["services"][0]["depends_on"] = ["redis"]
        cycle["services"][1]["depends_on"] = ["db"]
        mutations["dependency cycle"] = cycle

        for label, registry in mutations.items():
            with self.subTest(label), self.assertRaises(ValueError):
                runtime_generator.validate_registry(registry)


class BuildTests(unittest.TestCase):
    def test_project_makefile_exposes_supported_command_surface(self) -> None:
        makefile = (BUILD_ROOT / "Makefile").read_text()
        expected = {
            "generate",
            "validate",
            "build",
            "push",
            "manifest",
            "up",
            "down",
            "restart",
            "status",
            "logs",
            "runtime-validate",
            "rate-reset",
            "clean",
            "migrate",
            "seed",
            "smoke",
            "local",
            "local-stop",
            "local-restart",
            "local-status",
            "local-logs",
            "local-clean",
            "health",
            "health-local",
            "health-k8s",
            "test",
        }
        phony = set(
            next(
                line.removeprefix(".PHONY:").split()
                for line in makefile.splitlines()
                if line.startswith(".PHONY:")
            )
        )
        self.assertEqual(phony, expected)
        for target in expected:
            self.assertRegex(makefile, rf"(?m)^{target}\s*:[^\n]*$")

    def test_missing_dockerfile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(build_images, "ROOT", Path(temporary)):
                with self.assertRaisesRegex(SystemExit, "Missing Dockerfile"):
                    build_images.require_dockerfile(
                        {"key": "missing", "context": "missing"}
                    )

    def test_repository_and_platform_modes(self) -> None:
        image = {
            "key": "cml-memoryhive-backend",
            "context": "cml-memoryhive-backend",
            "dockerfile": "Dockerfile",
            "target": "production",
            "build_args": {},
        }
        local = build_images.build_command(
            image,
            registry="docker.io",
            namespace="maheshk172",
            version="v1.2.3",
            sha="abcdef012345",
            platforms="linux/amd64,linux/arm64",
            push=False,
            load=True,
        )
        pushed = build_images.build_command(
            image,
            registry="docker.io",
            namespace="maheshk172",
            version="v1.2.3",
            sha="abcdef012345",
            platforms="linux/amd64,linux/arm64",
            push=True,
            load=False,
        )
        self.assertIn(
            "docker.io/maheshk172/cml-memoryhive-backend:v1.2.3-abcdef0",
            local,
        )
        self.assertEqual(local[-2:], ["linux/amd64", "--load"])
        self.assertEqual(pushed[-2:], ["linux/amd64,linux/arm64", "--push"])

    def test_manifest_is_deterministic(self) -> None:
        config = runtime_generator.load_registry()
        kwargs = {
            "registry": config["registry"],
            "namespace": config["registry_namespace"],
            "version": "v1",
            "git_sha": "abcdef012345",
            "created_at": "2026-09-06T00:00:00Z",
        }
        first = image_manifest.build_manifest(config, **kwargs)
        second = image_manifest.build_manifest(config, **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["app"], "cml-memoryhive")
        self.assertEqual(
            first["runtime"]["cml-memoryhive-worker"],
            first["images"]["cml-memoryhive-backend"]["immutable"],
        )

    def test_generated_profiles_match_registry(self) -> None:
        tracked = {
            path: path.read_bytes()
            for path in sorted((BUILD_ROOT / "runtime").glob("docker-compose*.yml"))
        }
        subprocess.run(
            [sys.executable, str(BUILD_ROOT / "scripts/generate_runtime.py")],
            check=True,
        )
        first = {
            path: path.read_bytes()
            for path in sorted((BUILD_ROOT / "runtime").glob("docker-compose*.yml"))
        }
        subprocess.run(
            [sys.executable, str(BUILD_ROOT / "scripts/generate_runtime.py")],
            check=True,
        )
        second = {
            path: path.read_bytes()
            for path in sorted((BUILD_ROOT / "runtime").glob("docker-compose*.yml"))
        }
        self.assertEqual(tracked, first)
        self.assertEqual(first, second)
        config = runtime_generator.load_registry()
        descriptors = {service["key"]: service for service in config["services"]}
        for profile, expected in config["profiles"].items():
            compose = json.loads(
                (BUILD_ROOT / f"runtime/docker-compose.{profile}.yml").read_text()
            )
            actual = set(compose["services"]) - {"migrate"}
            self.assertEqual(actual, set(expected))
            for key in expected:
                if "command" in descriptors[key]:
                    self.assertEqual(
                        compose["services"][key].get("command"),
                        descriptors[key]["command"],
                    )
                if descriptors[key].get("image_key"):
                    image_descriptor = next(
                        image
                        for image in config["images"]
                        if image["key"] == descriptors[key]["image_key"]
                    )
                    expected_image = (
                        f"{config['registry']}/{config['registry_namespace']}/"
                        f"{descriptors[key]['image_key']}:local"
                    )
                    self.assertEqual(
                        compose["services"][key].get("image"), expected_image
                    )
                    self.assertEqual(
                        compose["services"][key]["build"]["dockerfile"],
                        image_descriptor["dockerfile"],
                    )
                    self.assertEqual(
                        compose["services"][key]["build"]["target"],
                        image_descriptor["runtime_target"],
                    )
                else:
                    self.assertEqual(
                        compose["services"][key].get("image"),
                        descriptors[key]["image"],
                    )
                expected_ports = runtime_generator.published_ports(descriptors[key])
                if expected_ports:
                    self.assertEqual(
                        compose["services"][key].get("ports"), expected_ports
                    )
                if "marker" in descriptors[key]["health"]:
                    self.assertEqual(
                        compose["services"][key]["healthcheck"]["test"][:5],
                        ["CMD", "uv", "run", "--frozen", "--no-sync"],
                    )
            health = json.loads(
                (
                    BUILD_ROOT / f"health_checker/health-registry.{profile}.json"
                ).read_text()
            )
            self.assertEqual(set(health["services"]), set(expected))
            for key, service in health["services"].items():
                self.assertEqual(service["key"], key)
                self.assertEqual(
                    service["host_port_env"], descriptors[key].get("host_port_env")
                )
                self.assertEqual(
                    service["kubernetes"], descriptors[key].get("kubernetes")
                )
            if "db" in expected:
                self.assertEqual(
                    health["services"]["db"]["kubernetes"],
                    {"kind": "statefulset", "name": "db"},
                )
            if "cml-memoryhive-worker" in expected:
                self.assertEqual(
                    health["services"]["cml-memoryhive-worker"]["kubernetes"],
                    {
                        "kind": "deployment",
                        "name": "cml-memoryhive-worker",
                    },
                )

    def test_backend_processes_are_uv_managed(self) -> None:
        config = runtime_generator.load_registry()
        for service in config["services"]:
            if service.get("image_key") == "cml-memoryhive-backend":
                self.assertEqual(
                    service["command"][:4],
                    ["uv", "run", "--frozen", "--no-sync"],
                )

    def test_production_compose_requires_pinned_images_and_uv(self) -> None:
        compose = yaml.safe_load(
            (BUILD_ROOT / "runtime/docker-compose.production.yml").read_text()
        )["services"]
        backend_image = "${BACKEND_IMAGE:?Set immutable BACKEND_IMAGE}"
        frontend_image = "${FRONTEND_IMAGE:?Set immutable FRONTEND_IMAGE}"
        for key in (
            "cml-memoryhive-backend",
            "cml-memoryhive-worker",
            "cml-memoryhive-temporal-worker",
            "cml-memoryhive-temporal-scheduler",
        ):
            self.assertEqual(backend_image, compose[key]["image"])
            self.assertIn(
                "uv run --frozen --no-sync", " ".join(compose[key]["command"])
            )
        self.assertEqual(frontend_image, compose["cml-memoryhive-frontend"]["image"])
        for key in (
            "cml-memoryhive-worker",
            "cml-memoryhive-temporal-worker",
            "cml-memoryhive-temporal-scheduler",
        ):
            self.assertEqual(
                compose[key]["healthcheck"]["test"][:5],
                ["CMD", "uv", "run", "--frozen", "--no-sync"],
            )
        production_example = dict(
            line.split("=", 1)
            for line in (REPO_ROOT / ".env.production.example").read_text().splitlines()
            if line and not line.startswith("#") and "=" in line
        )
        for key, project in (
            ("BACKEND_IMAGE", "backend"),
            ("FRONTEND_IMAGE", "frontend"),
        ):
            self.assertRegex(
                production_example[key],
                rf"^docker\.io/maheshk172/cml-memoryhive-{project}:v[^:]+-[0-9a-f]{{7}}$",
            )


class OrchestrationTests(unittest.TestCase):
    def test_port_conflicts_honor_profile_and_overrides(self) -> None:
        with patch.object(check_ports, "available", return_value=False):
            conflicts = check_ports.profile_conflicts(
                "infra", {"POSTGRES_PORT": "15432", "REDIS_PORT": "16379"}
            )
        self.assertEqual(
            conflicts,
            [
                ("db", 15432),
                ("redis", 16379),
                ("minio", 9000),
                ("minio:console", 9001),
            ],
        )

    def test_port_preflight_reads_env_file_with_process_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            env_file = Path(temporary) / ".env"
            env_file.write_text("BACKEND_PORT=18000\nREDIS_PORT=16379\n")
            with patch.dict(os.environ, {"BACKEND_PORT": "28000"}, clear=True):
                environment = check_ports.load_environment(env_file)
        self.assertEqual(environment["BACKEND_PORT"], "28000")
        self.assertEqual(environment["REDIS_PORT"], "16379")

    def test_local_dependency_order(self) -> None:
        services = local_manager.app_services("full")
        positions = {service["key"]: index for index, service in enumerate(services)}
        self.assertLess(
            positions["cml-memoryhive-backend"],
            positions["cml-memoryhive-frontend"],
        )

    def test_local_runtime_env_file_falls_back_to_example(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            example = root / ".env.example"
            example.write_text("BACKEND_PORT=8000\n", encoding="utf-8")
            with (
                patch.object(local_manager, "REPO_ROOT", root),
                patch.dict(os.environ, {}, clear=True),
            ):
                self.assertEqual(local_manager.runtime_env_file(), example)
                local = root / ".env"
                local.write_text("BACKEND_PORT=18000\n", encoding="utf-8")
                self.assertEqual(local_manager.runtime_env_file(), local)

    def test_local_commands_and_proxy_use_configured_app_ports(self) -> None:
        services = {
            service["key"]: service for service in local_manager.registry()["services"]
        }
        environment = {"BACKEND_PORT": "18000", "FRONTEND_PORT": "13000"}

        backend, _ = local_manager.command_for(
            services["cml-memoryhive-backend"], environment
        )
        frontend, _ = local_manager.command_for(
            services["cml-memoryhive-frontend"], environment
        )

        self.assertEqual(backend[backend.index("--port") + 1], "18000")
        self.assertEqual(frontend[frontend.index("--port") + 1], "13000")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env").write_text("BACKEND_PORT=18000\n", encoding="utf-8")
            with (
                patch.object(local_manager, "REPO_ROOT", root),
                patch.dict(os.environ, {}, clear=True),
            ):
                loaded = local_manager.load_env()
        self.assertEqual(loaded["VITE_PROXY_TARGET"], "http://127.0.0.1:18000")

    def test_local_start_dry_run_does_not_spawn_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(local_manager, "PIDS", Path(temporary) / ".pids"),
                patch.object(local_manager, "LOGS", Path(temporary) / ".logs"),
                patch.object(local_manager, "ensure_port"),
                patch.object(local_manager.subprocess, "run") as run,
                patch.object(local_manager.subprocess, "Popen") as popen,
            ):
                local_manager.start("app-only", dry_run=True)
        run.assert_called_once()
        popen.assert_not_called()

    def test_local_infrastructure_waits_for_health(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(local_manager, "PIDS", Path(temporary) / ".pids"),
                patch.object(local_manager, "LOGS", Path(temporary) / ".logs"),
                patch.object(local_manager.subprocess, "run"),
                patch.object(local_manager, "ensure_port"),
                patch.object(local_manager, "compose") as compose,
            ):
                local_manager.start("infra", dry_run=True)
        compose.assert_called_once_with(
            "infra",
            "up",
            "--detach",
            "--wait",
            "--wait-timeout",
            local_manager.START_TIMEOUT_SECONDS,
            "db",
            "redis",
            "minio",
            dry_run=True,
        )

    def test_local_port_preflight_happens_before_starting_anything(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.object(local_manager, "PIDS", Path(temporary) / ".pids"),
                patch.object(local_manager, "LOGS", Path(temporary) / ".logs"),
                patch.object(local_manager.subprocess, "run"),
                patch.object(
                    local_manager,
                    "ensure_port",
                    side_effect=[None, SystemExit("occupied")],
                ),
                patch.object(local_manager, "compose") as compose,
                patch.object(local_manager.subprocess, "Popen") as popen,
            ):
                with self.assertRaisesRegex(SystemExit, "occupied"):
                    local_manager.start("full", dry_run=False)
        compose.assert_not_called()
        popen.assert_not_called()

    def test_local_start_removes_only_stale_pid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pids = Path(temporary)
            stale = pids / "stale.pid"
            invalid = pids / "invalid.pid"
            active = pids / "active.pid"
            stale.write_text("99999999\n", encoding="utf-8")
            invalid.write_text("not-a-pid\n", encoding="utf-8")
            active.write_text(f"{os.getpid()}\n", encoding="utf-8")
            with patch.object(local_manager, "PIDS", pids):
                local_manager.clean_stale_pid_files()
            self.assertFalse(stale.exists())
            self.assertFalse(invalid.exists())
            self.assertTrue(active.exists())

    def test_local_clean_removes_stale_state_but_guards_live_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pids = root / ".pids"
            logs = root / ".logs"
            pids.mkdir()
            logs.mkdir()
            stale = pids / "stale.pid"
            log = logs / "stale.log"
            stale.write_text("99999999\n", encoding="utf-8")
            log.write_text("old output\n", encoding="utf-8")
            with (
                patch.object(local_manager, "PIDS", pids),
                patch.object(local_manager, "LOGS", logs),
            ):
                local_manager.clean(True)
                self.assertTrue(stale.exists())
                self.assertTrue(log.exists())
                local_manager.clean(False)
                self.assertFalse(stale.exists())
                self.assertFalse(log.exists())
                active = pids / "active.pid"
                active.write_text(f"{os.getpid()}\n", encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "active"):
                    local_manager.clean(False)
                self.assertTrue(active.exists())

    def test_local_status_uses_registry_driven_health_for_entire_profile(self) -> None:
        with patch.object(
            local_manager.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=7),
        ) as run:
            self.assertEqual(local_manager.status("temporal"), 7)
        command = run.call_args.args[0]
        self.assertEqual(command[-4:], ["--mode", "local", "--profile", "temporal"])

    def test_docker_cleanup_requires_confirmation(self) -> None:
        environment = dict(os.environ)
        environment.pop("CONFIRM_CLEAN", None)
        environment["ENV_FILE"] = str(REPO_ROOT / ".env.example")
        result = subprocess.run(
            [
                "sh",
                str(BUILD_ROOT / "runtime/manage_services_docker.sh"),
                "clean",
                "--profile",
                "infra",
            ],
            cwd=REPO_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("CONFIRM_CLEAN=cml-memoryhive", result.stderr)

    def test_docker_start_waits_for_declared_health(self) -> None:
        lifecycle = (BUILD_ROOT / "runtime/manage_services_docker.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'compose up --build --detach --wait --wait-timeout "$START_TIMEOUT_SECONDS"',
            lifecycle,
        )
        self.assertIn('check_ports.py" "$PROFILE" --env-file "$ENV_FILE"', lifecycle)

    def test_mocked_docker_and_kubernetes_health_modes(self) -> None:
        service = {
            "key": "cml-memoryhive-worker",
            "container": "cml-memoryhive-worker",
            "kubernetes": {
                "kind": "deployment",
                "name": "cml-memoryhive-worker",
            },
        }
        with (
            patch.object(health_check.shutil, "which", return_value="tool"),
            patch.object(
                health_check.subprocess,
                "run",
                return_value=SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"Status": "running", "Health": None}),
                ),
            ),
        ):
            self.assertEqual(health_check.docker_check(service), (True, "running"))
        with (
            patch.object(health_check.shutil, "which", return_value="tool"),
            patch.object(
                health_check.subprocess,
                "run",
                return_value=SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "Status": "running",
                            "Health": {
                                "Status": "healthy",
                                "Log": [{"Output": "response included spaces"}],
                            },
                        }
                    ),
                ),
            ),
        ):
            self.assertEqual(health_check.docker_check(service), (True, "healthy"))
        payload = json.dumps(
            {
                "spec": {"replicas": 1},
                "status": {"readyReplicas": 1, "availableReplicas": 1},
            }
        )
        with (
            patch.object(health_check.shutil, "which", return_value="tool"),
            patch.object(
                health_check.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout=payload),
            ),
        ):
            ok, message = health_check.kubernetes_check("cml-memoryhive-local", service)
        self.assertTrue(ok)
        self.assertIn("ready 1/1", message)

    def test_local_health_honors_generated_port_environment(self) -> None:
        service = {
            "key": "cml-memoryhive-backend",
            "kind": "service",
            "port": 8000,
            "host_port_env": "BACKEND_PORT",
            "health": {"type": "http", "path": "/health/ready"},
            "container": "cml-memoryhive-backend",
        }
        with patch.object(
            health_check, "http_check", return_value=(True, "ok")
        ) as http_check:
            self.assertEqual(
                health_check.local_check(
                    service, "127.0.0.1", 3.0, {"BACKEND_PORT": "18000"}
                ),
                (True, "ok"),
            )
        http_check.assert_called_once_with("127.0.0.1", 18000, "/health/ready", 3.0)

    def test_local_health_uses_docker_state_for_unpublished_infrastructure(
        self,
    ) -> None:
        service = {
            "key": "temporal-db",
            "kind": "infra",
            "port": 0,
            "host_port_env": None,
            "health": {"type": "process"},
            "container": "cml-memoryhive-temporal-db",
        }
        with patch.object(
            health_check, "docker_check", return_value=(True, "healthy")
        ) as docker_check:
            self.assertEqual(
                health_check.local_check(service, "127.0.0.1", 3.0, {}),
                (True, "healthy"),
            )
        docker_check.assert_called_once_with(service, "127.0.0.1", 3.0, {})

    def test_docker_health_falls_back_to_registry_probe(self) -> None:
        service = {
            "key": "temporal",
            "container": "cml-memoryhive-temporal",
            "port": 7233,
            "host_port_env": "TEMPORAL_PORT",
            "health": {"type": "tcp"},
        }
        with (
            patch.object(health_check.shutil, "which", return_value="docker"),
            patch.object(
                health_check.subprocess,
                "run",
                return_value=SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"Status": "running", "Health": None}),
                ),
            ),
            patch.object(
                health_check, "tcp_check", return_value=(True, "tcp ok")
            ) as tcp_check,
        ):
            self.assertEqual(
                health_check.docker_check(
                    service,
                    "127.0.0.1",
                    2.0,
                    {"TEMPORAL_PORT": "17233"},
                ),
                (True, "tcp ok"),
            )
        tcp_check.assert_called_once_with("127.0.0.1", 17233, 2.0)


if __name__ == "__main__":
    unittest.main()
