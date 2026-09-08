# cml-memoryhive-build

Registry-driven image builds, local runtime orchestration, and health checking for Memoryhive.

Install the repository tooling environment first with `uv sync --locked` from the repository root.

`service-registry.json` is the canonical source for images, services, ports, dependencies, health contracts, and the `infra`, `app-only`, `full`, and `temporal` profiles.

```bash
make -C cml-memoryhive-build generate
make -C cml-memoryhive-build build VERSION=local
make -C cml-memoryhive-build up PROFILE=full
make -C cml-memoryhive-build local PROFILE=full
make -C cml-memoryhive-build health PROFILE=full
```

Multi-platform builds are pushed with `make push`; local builds load the first configured platform. Docker cleanup requires `CONFIRM_CLEAN=cml-memoryhive`.
