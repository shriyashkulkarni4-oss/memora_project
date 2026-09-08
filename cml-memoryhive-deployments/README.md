# cml-memoryhive-deployments

Template-driven Kubernetes generation and lifecycle management for Memoryhive.

Install the repository tooling environment first with `uv sync --locked` from the repository root.

```bash
make -C cml-memoryhive-deployments validate-all
make -C cml-memoryhive-deployments apply ENV=local PROFILE=full SECRET_ENV_FILE=../.env
make -C cml-memoryhive-deployments upgrade ENV=staging PROFILE=full SECRET_ENV_FILE=/secure/staging.env
```

`image-versions.json` is the sole source of deployed images. Generated manifests contain no Secrets. `apply` and `upgrade` create per-service Secrets from process environment values or `--secret-env-file` and stream them directly to `kubectl`.

Cluster mutations require the exact context configured for the selected environment. Namespace deletion additionally requires `CONFIRM_DELETE=cml-memoryhive`.
