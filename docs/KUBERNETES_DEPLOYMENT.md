# Kubernetes Deployment

Memoryhive keeps build metadata and Kubernetes deployment assets in this repo:

- `build/services.json` is the source of truth for container image names, build contexts, targets, and runtime image reuse.
- `build/scripts/generate_image_manifest.py` writes `build/output/image-versions.json`, the CI handoff artifact for deployments.
- `k8s/config/environments.json` defines namespaces, expected kubectl contexts, domains, replica counts, resources, and storage sizes.
- `k8s/config/profiles.json` defines deployable service groups.
- `k8s/image-versions.json` pins the images used by each environment until a release manifest is promoted.
- `k8s/scripts/manage.py` renders manifests and wraps cluster operations.

## Local Commands

```bash
make build-manifest IMAGE_VERSION=local
make k8s-generate K8S_ENV=local K8S_PROFILE=full
make k8s-validate K8S_ENV=local K8S_PROFILE=full
python3 health_checker/health_check.py --mode local backend frontend
```

Generated manifests are written to `k8s/generated/<environment>/<profile>/` and
are intentionally ignored by Git. Inspect them before applying to a cluster.

## Cluster Commands

```bash
python3 k8s/scripts/manage.py apply staging full
python3 k8s/scripts/manage.py upgrade staging full
python3 k8s/scripts/manage.py status staging full
python3 k8s/scripts/manage.py rollback staging full backend
CONFIRM_DELETE=memoryhive python3 k8s/scripts/manage.py delete staging full
```

Mutating commands refuse to run unless the active kubectl context matches the
environment's `expected_context`. Use `--skip-context-check` only for throwaway
clusters or CI jobs where the context name is controlled elsewhere.

## Secrets

Rendered `Secret` manifests contain placeholders only. Replace them through the
cluster's secret-management path before production use, or wire an operator such
as External Secrets. Do not commit real database, JWT, MinIO, Redis, n8n, or
encryption secrets.

## Release Flow

Tagged releases publish backend and frontend images to GHCR with three tags:
`<version>-<short_sha>`, `<version>`, and `latest`. The immutable
`<version>-<short_sha>` tag is also written to the image manifest artifact.
Promote that manifest by copying the relevant image refs into
`k8s/image-versions.json` or by having the deployment automation update the pin
file in a follow-up release process.
