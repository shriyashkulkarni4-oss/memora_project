# Memoryhive Build and Kubernetes Deployment

Memoryhive follows the split build and deployment project pattern:

- `cml-memoryhive-build/service-registry.json` is canonical for images, runtime services, ports, dependencies, health checks, and profiles.
- `cml-memoryhive-build/` builds/pushes images, generates local Compose profiles, runs local processes, and checks health.
- `cml-memoryhive-deployments/image-versions.json` is the only source of deployed image references.
- `cml-memoryhive-deployments/` renders non-secret manifests and owns cluster lifecycle commands.

## Build and local runtime

```bash
make runtime-generate
make build-images IMAGE_VERSION=local
make runtime-up PROFILE=full
make health-local PROFILE=full
make runtime-down PROFILE=full
```

For infra in Docker and hot-reloading services as host processes:

```bash
cml-memoryhive-build/runtime/manage_services_local.sh start --profile full
cml-memoryhive-build/runtime/manage_services_local.sh status --profile full
cml-memoryhive-build/runtime/manage_services_local.sh stop --profile full
```

## Generate and validate deployments

The supported environments are `local`, `staging`, and `production`. Each can render `infra`, `app-only`, `full`, or `temporal`.

```bash
make -C cml-memoryhive-deployments validate-all
make k8s-generate K8S_ENV=local K8S_PROFILE=full
```

Tracked non-secret output is written to `cml-memoryhive-deployments/generated/<environment>/<profile>/cml-memoryhive.yaml`. Secret resources are never written there.

## Cluster lifecycle

Mutating commands require the exact Kubernetes context configured for the environment. Supply secrets through process environment values or an ignored environment file.

```bash
python3 cml-memoryhive-deployments/scripts/manage.py apply staging full --secret-env-file /secure/staging.env
python3 cml-memoryhive-deployments/scripts/manage.py upgrade staging full --secret-env-file /secure/staging.env
python3 cml-memoryhive-deployments/scripts/manage.py status staging full
python3 cml-memoryhive-deployments/scripts/manage.py rollback staging full cml-memoryhive-backend
CONFIRM_DELETE=cml-memoryhive python3 cml-memoryhive-deployments/scripts/manage.py delete staging full
```

`apply` and `upgrade` stream Secrets directly to `kubectl`. Staging and production reject missing values and known development placeholders. Upgrades compare deployed images with immutable pins and wait only for changed deployments.

## Promotion

A tagged release builds both multi-architecture images with the build project's scripts, scans them, emits `cml-memoryhive-image-versions`, and opens a staging promotion PR. The protected `Promote Production` workflow copies the exact staging immutable tags into production and opens a separate PR. Neither workflow commits directly to the default branch.
