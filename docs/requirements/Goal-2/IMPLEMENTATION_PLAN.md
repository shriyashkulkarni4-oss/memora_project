# Goal 2 — Standardize Memoryhive Projects, Builds, and Deployments

## Summary

Reorganize the monorepo around the Zestro blueprint while preserving application behavior. Use `cml-memoryhive-*` consistently for every first-party project, image, Compose identity, Kubernetes workload, CI artifact, and package name.

This approved plan was persisted before implementation changes began.

## Project and Naming Changes

- Atomically rename the first-party projects, with no compatibility symlinks:
  - `backend/` → `cml-memoryhive-backend/`
  - `frontend/` → `cml-memoryhive-frontend/`
  - `mobile/` → `cml-memoryhive-mobile/`
  - `automation/` → `cml-memoryhive-automation/`
  - Consolidate `build/`, local Compose orchestration, and `health_checker/` into `cml-memoryhive-build/`.
  - Move `k8s/` into `cml-memoryhive-deployments/`.
- Retain `docs/`, `ops/`, and `scripts/` as shared repository support rather than standalone projects.
- Rename Python/npm package metadata to `cml-memoryhive-backend`, `cml-memoryhive-frontend`, `cml-memoryhive-mobile`, and `cml-memoryhive-automation`. Preserve the customer-facing Memoryhive name and existing mobile bundle/application IDs.
- Prefix first-party runtime identities:
  - Images: `docker.io/maheshk172/cml-memoryhive-backend` and `docker.io/maheshk172/cml-memoryhive-frontend`.
  - Workloads/services: `cml-memoryhive-backend`, `cml-memoryhive-worker`, `cml-memoryhive-temporal-worker`, `cml-memoryhive-temporal-scheduler`, and `cml-memoryhive-frontend`.
  - Compose project, Kubernetes namespaces/resources, CI artifacts, generated manifests, and confirmation tokens use `cml-memoryhive`.
  - Keep third-party dependency names concise: `db`, `redis`, `minio`, `temporal`, and `temporal-db`.
- Update every active path reference in workflows, Dockerfiles/Compose, scripts, tests, release tooling, documentation, `.gitignore`, `AGENTS.md`, and the knowledge generator. Preserve historical Goal 1/archive content, adding a Goal 2 path-mapping note rather than rewriting historical evidence.
- Coordinate renaming the GitHub origin from `cml-memora` to `cml-memoryhive` and update the local remote after the external rename.

## Build Project

- Structure `cml-memoryhive-build/` into `build/`, `runtime/`, and `health_checker/`, with a project Makefile as the supported entry point.
- Introduce one canonical JSON service registry containing:
  - First-party and infrastructure service keys, ports, health probes, dependencies, source/Dockerfile paths, image ownership, and profile membership.
  - Profiles `infra`, `app-only`, `full`, and `temporal`.
  - Runtime processes that reuse the backend image.
- Generate Compose and health configuration from this registry so build scripts, runtime profiles, and health modes cannot maintain divergent service lists.
- Preserve `{version}-{short_sha}` immutable tags plus release and `latest` tags. Multi-architecture pushes target `linux/amd64,linux/arm64`; local loads use one selected platform.
- Provide:
  - All-Docker lifecycle commands with profile selection, port-conflict checks, status, logs, safe cleanup, migration, seed, and smoke-test hooks.
  - Infra-in-Docker/services-local mode with dependency ordering, hot reload, `.logs/`, `.pids/`, and stale-process cleanup.
  - Registry-driven local, Docker, and Kubernetes health checks, including worker and Temporal process probes.
- Make release CI call the same registry-driven build commands used locally instead of maintaining a separate image matrix.

## Deployment Project and Promotion

- Structure `cml-memoryhive-deployments/` with a Makefile, deployment CLI, environment/profile configuration, image pins, YAML templates, deterministic generated manifests, and documentation.
- Retain `local`, `staging`, and `production` plus `infra`, `app-only`, `full`, and `temporal`; rename owned resources and namespaces to `cml-memoryhive-*`.
- Use readable YAML templates selected and populated by Python with:
  - Per-workload Deployment/StatefulSet, Service, ConfigMap, apply-only Secret reference, and ServiceAccount resources.
  - Namespace quota/limits, ingress, default-deny and allow policies, probes, replica/resource settings, persistent storage, and backend migration init container.
  - No production seed step because Memoryhive has no required baseline production dataset; demo seeding remains explicit.
- Track non-secret generated manifests at `generated/<environment>/<profile>/cml-memoryhive.yaml`.
- Rendering must use an explicit variable allow-list and reject unresolved tokens.
- Remove committed secret values from generated manifests. The deployment CLI will build per-service Secrets from an ignored environment file or CI environment and stream them directly to `kubectl`; staging/production fail if required values are missing or placeholders.
- Expose `generate`, `validate`, `apply`, `upgrade`, `rollback`, `status`, and confirmation-guarded `delete` commands. Cluster mutations require an exact expected-context match; upgrades diff immutable image pins and wait for each rollout with a timeout.
- Make `image-versions.json` the sole deployment image source:
  - Successful tagged releases open a staging promotion PR containing immutable pin and regenerated-manifest changes.
  - Production promotion is a manually dispatched, protected workflow that copies the exact staging immutable tags and opens a separate PR.
  - Promotion workflows never commit directly to the default branch.
- Update the deployment workflow to use the new CLI and protected GitHub environments.

## Validation and Acceptance

- Add registry tests for schema validity, unique names/ports, dependency cycles, Dockerfile existence, profile membership, and runtime-to-image mappings.
- Test build command/tag generation, missing Dockerfiles, local versus multi-architecture behavior, and deterministic image-manifest output.
- Validate every Compose profile with `docker compose config`; test orchestration dry runs, port conflicts, dependency ordering, cleanup guards, and mocked health modes.
- Render all 12 environment/profile combinations and verify:
  - YAML parsing and `kubectl --dry-run=client`.
  - Correct `cml-memoryhive-*` resources and pinned images.
  - Ingress/network-policy flags materially change output.
  - Profiles omit excluded services.
  - No unresolved variables, real secrets, or production placeholders are committed.
- Test staging and production promotion scripts for target-environment isolation, immutable-tag enforcement, no-op behavior, and exact staging-to-production promotion.
- Run backend, frontend, mobile, automation, container, deployment, and knowledge checks from renamed paths.
- Add a naming audit that rejects obsolete active references such as `cml-memora`, `memoryhive-backend`, and old short project paths, excluding historical Goal 1/archive records.
- Preserve all unrelated and currently uncommitted user changes, especially the existing Goal 1 and knowledge-generator edits.

## Assumptions

- “frontnend” means `cml-memoryhive-frontend`.
- This remains one Git monorepo containing multiple prefixed project directories.
- The restructuring is atomic; downstream consumers must switch to the new paths and names in the same release.
- Staging promotion is automatic through a PR; production promotion is manual through a separate protected PR.
- The current application APIs, database schema, public Memoryhive branding, domains, and mobile store identity remain unchanged.
