#!/usr/bin/env node
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const argv = process.argv.slice(2);

const FLAGS = new Set([
  "--cleanup",
  "--cleanup-only",
  "--clean-volumes",
  "--docker",
  "--doctor",
  "--dry-run",
  "--help",
  "--seed-only",
  "--skip-mobile",
  "--skip-seed",
  "--skip-smoke",
  "--skip-web",
  "--temporal",
]);
const VALUE_FLAGS = new Set(["--base-url", "--persona"]);

function help() {
  console.log(`Memoryhive automation runner

Usage:
  npm --prefix cml-memoryhive-automation run test -- [options]

Options:
  --docker            Start the Compose dev stack before running checks
  --temporal          Start the Compose Temporal profile before running checks
  --cleanup           Stop Compose services after the run
  --clean-volumes     Run the build runtime clean command; requires CONFIRM_CLEAN=cml-memoryhive
  --seed-only         Load demo data, then exit
  --skip-seed         Do not run seed_data.py
  --skip-smoke        Do not run ops/smoke.sh
  --skip-web          Do not run frontend live Playwright
  --skip-mobile       Do not run mobile Expo-web Playwright
  --base-url URL      Backend origin; default BASE_URL or http://localhost:8000
  --persona NAME      Seed persona; default SEED_PERSONA or all
  --dry-run           Print commands without executing them
`);
}

function valueFlag(name, fallback) {
  const index = argv.indexOf(name);
  if (index === -1) return fallback;
  const value = argv[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`${name} requires a value`);
  }
  return value;
}

function hasFlag(name) {
  return argv.includes(name);
}

function validateArgs() {
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (VALUE_FLAGS.has(arg)) {
      index += 1;
      continue;
    }
    if (!FLAGS.has(arg)) {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
}

function toApiUrl(baseUrl) {
  const normalized = baseUrl.replace(/\/$/, "");
  return normalized.endsWith("/api/v1") ? normalized : `${normalized}/api/v1`;
}

function requirePath(path) {
  if (!existsSync(resolve(ROOT, path))) {
    throw new Error(`Missing required automation dependency: ${path}`);
  }
}

async function run(command, args, options = {}) {
  const cwd = options.cwd ? resolve(ROOT, options.cwd) : ROOT;
  const printable = [command, ...args].join(" ");
  console.log(`\n+ ${printable}`);
  if (hasFlag("--dry-run")) return;
  await new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd,
      env: { ...process.env, ...options.env },
      stdio: "inherit",
    });
    child.on("error", reject);
    child.on("exit", (code, signal) => {
      if (code === 0) {
        resolvePromise();
        return;
      }
      reject(new Error(`${printable} failed with ${signal ?? `exit ${code}`}`));
    });
  });
}

async function captureSanitizedLogs() {
  const artifactRoot = resolve(ROOT, "cml-memoryhive-backend/evaluation-results");
  mkdirSync(artifactRoot, { recursive: true });
  const args = [
    "compose", "--env-file", resolve(ROOT, ".env"),
    "-f", resolve(ROOT, "cml-memoryhive-build/runtime/docker-compose.temporal.yml"),
    "logs", "--no-color", "--tail", "300",
  ];
  const output = await new Promise((resolveOutput) => {
    const child = spawn("docker", args, { cwd: ROOT, env: process.env });
    let value = "";
    child.stdout.on("data", (chunk) => { value += chunk; });
    child.stderr.on("data", (chunk) => { value += chunk; });
    child.on("error", (error) => resolveOutput(String(error)));
    child.on("exit", () => resolveOutput(value));
  });
  const sanitized = output
    .replace(/(authorization|api[_-]?key|token|password)([=: ]+)[^\s,;]+/gi, "$1$2[REDACTED]")
    .replace(/Bearer\s+[^\s]+/gi, "Bearer [REDACTED]");
  writeFileSync(resolve(artifactRoot, "temporal-compose-sanitized.log"), sanitized);
}

async function doctor({ useDocker }) {
  [
    "seed_data.py",
    "cml-memoryhive-build/runtime/manage_services_docker.sh",
    "ops/smoke.sh",
    "cml-memoryhive-frontend/package.json",
    "cml-memoryhive-mobile/package.json",
  ].forEach(requirePath);
  await run("node", ["--version"]);
  await run("uv", ["--version"]);
  if (useDocker) {
    await run("docker", ["compose", "version"]);
  }
}

async function stopStack({ cleanVolumes, profile }) {
  if (cleanVolumes) {
    await run("sh", ["cml-memoryhive-build/runtime/manage_services_docker.sh", "clean", "--profile", profile]);
    return;
  }
  await run("sh", ["cml-memoryhive-build/runtime/manage_services_docker.sh", "stop", "--profile", profile]);
}

async function main() {
  validateArgs();
  if (hasFlag("--help")) {
    help();
    return;
  }

  const baseUrl = valueFlag("--base-url", process.env.BASE_URL ?? "http://localhost:8000");
  const apiUrl = toApiUrl(baseUrl);
  const persona = valueFlag("--persona", process.env.SEED_PERSONA ?? "all");
  const useDocker = hasFlag("--docker") || hasFlag("--temporal");
  const cleanVolumes = hasFlag("--clean-volumes");
  const runtimeProfile = hasFlag("--temporal") ? "temporal" : "full";

  await doctor({ useDocker });
  if (hasFlag("--doctor")) return;

  if (hasFlag("--cleanup-only")) {
    await stopStack({ cleanVolumes, profile: runtimeProfile });
    return;
  }

  try {
    if (useDocker) {
      await run("sh", [
        "cml-memoryhive-build/runtime/manage_services_docker.sh",
        "start",
        "--profile",
        runtimeProfile,
      ]);
      await run("sh", ["cml-memoryhive-build/runtime/manage_services_docker.sh", "validate", "--profile", runtimeProfile]);
      await run("sh", ["cml-memoryhive-build/runtime/manage_services_docker.sh", "rate-reset", "--profile", runtimeProfile]);
    }

    if (!hasFlag("--skip-seed")) {
      await run("uv", [
        "run",
        "python",
        "seed_data.py",
        "--base-url",
        baseUrl,
        "--persona",
        persona,
      ]);
    }
    if (hasFlag("--seed-only")) return;

    if (!hasFlag("--skip-smoke")) {
      await run("sh", ["ops/smoke.sh"], { env: { BASE_URL: baseUrl } });
    }
    if (hasFlag("--temporal")) {
      await run("uv", ["run", "python", "scripts/run_ai_evaluations.py", "--output", "evaluation-results/offline-acceptance.json"], { cwd: "cml-memoryhive-backend" });
      await run("uv", ["run", "python", "scripts/temporal_acceptance.py", "--base-url", baseUrl, "--output", "evaluation-results/temporal-acceptance.json"], { cwd: "cml-memoryhive-backend" });
      await run("uv", ["run", "pytest", "-q", "tests/test_temporal_workflows.py", "tests/test_temporal_stages.py", "tests/test_analysis_dispatch.py", "tests/test_ai_gateway.py", "tests/test_openrouter.py", "tests/test_huggingface.py", "tests/test_openai_compatible.py", "tests/test_local_automation_providers.py"], { cwd: "cml-memoryhive-backend" });
      await run("uv", ["run", "python", "scripts/load_acceptance.py", "--base-url", baseUrl, "--output", "evaluation-results/load-acceptance.json"], { cwd: "cml-memoryhive-backend" });
    }
    if (!hasFlag("--skip-web")) {
      await run("npm", ["--prefix", "cml-memoryhive-frontend", "run", "test:e2e:live"], {
        env: { BASE_URL: baseUrl, MEMORYHIVE_API_URL: apiUrl, VITE_API_URL: apiUrl },
      });
    }
    if (!hasFlag("--skip-mobile")) {
      await run("npm", ["--prefix", "cml-memoryhive-mobile", "run", "test:e2e:web"], {
        env: {
          BASE_URL: baseUrl,
          EXPO_PUBLIC_API_URL: apiUrl,
          MEMORYHIVE_API_URL: apiUrl,
        },
      });
    }
  } catch (error) {
    if (hasFlag("--temporal")) await captureSanitizedLogs();
    throw error;
  } finally {
    if (useDocker && hasFlag("--cleanup")) {
      await stopStack({ cleanVolumes, profile: runtimeProfile });
    }
  }
}

main().catch((error) => {
  console.error(`\nAutomation failed: ${error.message}`);
  process.exitCode = 1;
});
