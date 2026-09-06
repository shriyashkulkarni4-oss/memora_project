# Goal 1 Validation Results

Last verified: 2026-09-06

## Executed Repository Gates

| Surface | Command | Result |
| --- | --- | --- |
| Backend | `cd backend && ./.venv/bin/ruff check app tests` | Pass |
| Backend | `cd backend && ./.venv/bin/black --check app tests` | Pass; 56 files unchanged |
| Backend | `cd backend && ./.venv/bin/python -m pytest -q` | Pass; 35 tests |
| Frontend | `npm --prefix frontend run lint` | Pass; zero warnings |
| Frontend | `npm --prefix frontend test` | Pass; 17 tests in 5 files |
| Frontend | `npm --prefix frontend run build` | Pass; TypeScript and Vite production build |
| Mobile | `npm --prefix mobile run typecheck` | Pass |
| Mobile | `npm --prefix mobile run lint` | Pass |
| Mobile | `npm --prefix mobile test` | Pass; 61 tests in 14 files |
| Mobile | `cd mobile && npx expo export --platform web` | Pass; 18 static routes |
| Store packet | `npm --prefix mobile run store:submission:check` | Pass; current |
| Store readiness | `npm --prefix mobile run store:check:ci` | Pass; 47 OK, 0 warnings, 0 repository blockers, 16 release blockers |
| Container config | `docker compose --env-file .env.production.example -f docker-compose.prod.yml config --quiet` | Pass |
| Ops shell syntax | `sh -n ops/*.sh` | Pass |
| Deployment syntax | `python3 -m py_compile build/scripts/*.py k8s/scripts/*.py health_checker/*.py` | Pass |
| Automation syntax | `node --check automation/scripts/run.mjs` | Pass |
| Automation plan | `npm --prefix automation run dry-run` | Pass |
| Image tooling | Generate manifest plus image-build dry run | Pass |
| Kubernetes | Validate `local/full` and `local/temporal` profiles | Pass |
| Knowledge | `python3 scripts/generate_knowledge.py --check` | Pass |
| Worktree formatting | `git diff --check` and status-document whitespace scan | Pass |
| Status links | Resolve every local link in `Goal Status/*.md` | Pass |

The backend test run emits two non-blocking deprecation warnings from the
Starlette/FastAPI test client and AnyIO compatibility layer. No application
test failed.

## Runtime Evidence

The most recent full Docker-backed automation run on 2026-09-06:

- rebuilt and health-checked PostgreSQL, MinIO, Redis, FastAPI, the processing
  worker, and the React frontend;
- applied migrations and idempotently seeded 53 items across four personas;
- passed authenticated API smoke checks;
- passed the web and Expo-web Playwright workflows; and
- stopped the stack while preserving volumes.

The authoritative scenario detail is in
[`docs/APP_TEST_REPORT.md`](../../APP_TEST_REPORT.md). The later handoff changes
are documentation and tests only; runtime source was not changed after that
Docker run.

## External Checks Not Yet Proven

| Check | Current evidence | Completion proof required |
| --- | --- | --- |
| Expo/EAS identity | CLI reports `Not logged in`; no project ID | Authenticated EAS project and committed ID |
| EAS production environment/signing | Example manifest only | Completed `eas-release-evidence.json` |
| Signed iOS build | No recorded `.ipa` | Artifact plus EAS build ID |
| Signed Android build | No recorded `.aab`/`.apk` | Artifact plus EAS build ID |
| Physical-device behavior | No final native records | Two device records per platform |
| Android target and permissions | Source policy only | Native artifact target SDK and permission inspection |
| Production compliance URLs/contact | Placeholders | Public routes and real support contact |
| Store review access | Placeholder email, no committed password by design | Dedicated account entered out of band |
| Apple/Google forms and privacy review | Example manifest only | Completed `store-console-evidence.json` |

## Final Acceptance Gate

After the external inputs are available, regenerate the store packet with the
same protected release env file used for validation, then run:

```sh
npm --prefix mobile run store:submission:check -- --release-env-file /secure/path/release.env
npm --prefix mobile run store:check -- --strict --release-env-file /secure/path/release.env
```

Goal 1 can be marked complete only when the strict command exits successfully
with zero repository and zero release blockers.

