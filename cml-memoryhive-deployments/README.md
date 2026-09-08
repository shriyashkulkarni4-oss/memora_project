# cml-memoryhive-deployments

Template-driven Kubernetes generation and lifecycle management for Memoryhive.

Install the repository tooling environment first with `uv sync --locked` from the repository root.

```bash
make -C cml-memoryhive-deployments validate-all
make -C cml-memoryhive-deployments readiness-all
make -C cml-memoryhive-deployments apply ENV=local PROFILE=full SECRET_ENV_FILE=../.env
make -C cml-memoryhive-deployments upgrade ENV=staging PROFILE=full SECRET_ENV_FILE=/secure/staging.env
```

`image-versions.json` is the sole source of deployed images. Generated manifests contain no Secrets. `apply` and `upgrade` create per-service Secrets from process environment values or `--secret-env-file` and stream them directly to `kubectl`.

Each Kubernetes kind has a readable template under `templates/`; the Python renderer selects the template, permits only its declared variables, and rejects unresolved tokens. `validate` renders the selected bundle, parses its YAML, and performs a real `kubectl apply --dry-run=client --validate=false` check.

The checked-in non-local configuration can be rendered for review before the first release. Cluster-mutating `apply` and `upgrade` commands additionally reject reserved example domains, placeholder Temporal endpoints, floating tags, and zero-version image pins. Replace those values through the release/promotion process and environment configuration before deployment.

`readiness-all` is the strict release gate. Unlike review-oriented `validate-all`, it
fails while staging or production still contains example endpoints or placeholder
image pins. The root `make goal-2-readiness` target runs the complete local test suite
before this strict gate.

Cluster mutations require the exact context configured for the selected environment. Namespace deletion additionally requires `CONFIRM_DELETE=cml-memoryhive`.
