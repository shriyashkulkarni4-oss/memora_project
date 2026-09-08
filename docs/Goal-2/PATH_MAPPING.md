# Goal 2 Path Mapping

Goal 1 and archived records preserve the paths and commands that were accurate when
their evidence was captured. For current work, interpret those historical paths using
this mapping:

| Historical path | Current path |
| --- | --- |
| `backend/` | `cml-memoryhive-backend/` |
| `frontend/` | `cml-memoryhive-frontend/` |
| `mobile/` | `cml-memoryhive-mobile/` |
| `automation/` | `cml-memoryhive-automation/` |
| `build/` | `cml-memoryhive-build/build/` |
| `health_checker/` | `cml-memoryhive-build/health_checker/` |
| Root local Compose files | `cml-memoryhive-build/runtime/` |
| `k8s/` | `cml-memoryhive-deployments/` |

`docs/`, `ops/`, and `scripts/` remain shared repository support directories. This
mapping is informational; historical Goal 1/archive content must not be rewritten to
make old evidence appear as if it ran from the new locations.
