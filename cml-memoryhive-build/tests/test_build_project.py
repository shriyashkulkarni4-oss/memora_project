from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

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
image_manifest = module("image_manifest", BUILD_ROOT / "build/scripts/generate_image_manifest.py")
runtime_generator = module("runtime_generator", BUILD_ROOT / "scripts/generate_runtime.py")


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads((BUILD_ROOT / "service-registry.json").read_text())

    def test_registry_integrity(self) -> None:
        services = self.registry["services"]
        keys = [item["key"] for item in services]
        self.assertEqual(len(keys), len(set(keys)))
        images = {item["key"] for item in self.registry["images"]}
        self.assertEqual(images, {"cml-memoryhive-backend", "cml-memoryhive-frontend"})
        host_ports = [item["host_port"] for item in services if item.get("host_port")]
        self.assertEqual(len(host_ports), len(set(host_ports)))
        for profile, members in self.registry["profiles"].items():
            self.assertTrue(members, profile)
            self.assertFalse(set(members) - set(keys), profile)
        for service in services:
            self.assertFalse(set(service["depends_on"]) - set(keys), service["key"])
            if service.get("image_key"):
                self.assertIn(service["image_key"], images)

    def test_dependency_graph_is_acyclic(self) -> None:
        graph = {item["key"]: set(item["depends_on"]) for item in self.registry["services"]}
        while graph:
            ready = {key for key, dependencies in graph.items() if not dependencies & graph.keys()}
            self.assertTrue(ready, f"dependency cycle: {graph}")
            graph = {key: dependencies - ready for key, dependencies in graph.items() if key not in ready}

    def test_all_dockerfiles_exist(self) -> None:
        for image in self.registry["images"]:
            self.assertTrue((REPO_ROOT / image["context"] / image["dockerfile"]).is_file())


class BuildTests(unittest.TestCase):
    def test_repository_and_platform_modes(self) -> None:
        image = {"key": "cml-memoryhive-backend", "context": "cml-memoryhive-backend", "dockerfile": "Dockerfile", "target": "production", "build_args": {}}
        local = build_images.build_command(image, registry="ghcr.io", namespace="coding-monkey-labs-client-projects", version="v1.2.3", sha="abcdef012345", platforms="linux/amd64,linux/arm64", push=False, load=True)
        pushed = build_images.build_command(image, registry="ghcr.io", namespace="coding-monkey-labs-client-projects", version="v1.2.3", sha="abcdef012345", platforms="linux/amd64,linux/arm64", push=True, load=False)
        self.assertIn("ghcr.io/coding-monkey-labs-client-projects/cml-memoryhive-backend:v1.2.3-abcdef0", local)
        self.assertEqual(local[-2:], ["linux/amd64", "--load"])
        self.assertEqual(pushed[-2:], ["linux/amd64,linux/arm64", "--push"])

    def test_manifest_is_deterministic(self) -> None:
        config = runtime_generator.load_registry()
        kwargs = {"registry": config["registry"], "namespace": config["registry_namespace"], "version": "v1", "git_sha": "abcdef012345", "created_at": "2026-09-06T00:00:00Z"}
        first = image_manifest.build_manifest(config, **kwargs)
        second = image_manifest.build_manifest(config, **kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["app"], "cml-memoryhive")
        self.assertEqual(first["runtime"]["cml-memoryhive-worker"], first["images"]["cml-memoryhive-backend"]["immutable"])

    def test_generated_profiles_match_registry(self) -> None:
        subprocess.run([sys.executable, str(BUILD_ROOT / "scripts/generate_runtime.py")], check=True)
        config = runtime_generator.load_registry()
        descriptors = {service["key"]: service for service in config["services"]}
        for profile, expected in config["profiles"].items():
            compose = json.loads((BUILD_ROOT / f"runtime/docker-compose.{profile}.yml").read_text())
            actual = set(compose["services"]) - {"migrate"}
            self.assertEqual(actual, set(expected))
            for key in expected:
                if "command" in descriptors[key]:
                    self.assertEqual(compose["services"][key].get("command"), descriptors[key]["command"])
                if descriptors[key].get("image_key"):
                    expected_image = (
                        f"{config['registry']}/{config['registry_namespace']}/"
                        f"{descriptors[key]['image_key']}:local"
                    )
                    self.assertEqual(compose["services"][key].get("image"), expected_image)
            health = json.loads((BUILD_ROOT / f"health_checker/health-registry.{profile}.json").read_text())
            self.assertEqual(set(health["services"]), set(expected))

    def test_backend_processes_are_uv_managed(self) -> None:
        config = runtime_generator.load_registry()
        for service in config["services"]:
            if service.get("image_key") == "cml-memoryhive-backend":
                self.assertEqual(service["command"][:3], ["uv", "run", "--frozen"])


if __name__ == "__main__":
    unittest.main()
