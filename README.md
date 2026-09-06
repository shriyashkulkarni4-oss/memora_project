# Memoryhive

Memoryhive is an offline-first personal library for capturing, processing, and
finding links, screenshots, and text. The repository contains a React web app,
an Expo iOS/Android app, a FastAPI API and worker, PostgreSQL, MinIO, and Redis.

## Service contract

| Service | Development URL | Purpose |
| --- | --- | --- |
| Frontend | http://localhost:3000 | Vite development server |
| Backend | http://localhost:8000 | FastAPI application |
| API v1 | http://localhost:8000/api/v1 | Versioned application API |
| API docs | http://localhost:8000/docs | OpenAPI UI |
| Health | http://localhost:8000/health | Backend health check |
| MinIO API | http://localhost:9000 | S3-compatible object storage |
| MinIO console | http://localhost:9001 | Object storage administration |
| PostgreSQL | localhost:5432 | Application database |
| Mobile web preview | http://localhost:8083 | Expo development preview |

Host ports can be changed in `.env`. Internal container ports and service names remain stable.

## Docker development

Requirements: Docker Engine with Docker Compose v2 or newer.

```bash
cp .env.example .env
docker compose up --build
```

Useful commands:

```bash
# Start in the background
docker compose up --build --detach

# Follow application logs
docker compose logs --follow backend frontend

# Apply database migrations
docker compose exec backend alembic upgrade head

# Stop containers without deleting data
docker compose down
```

The same local lifecycle is wrapped by `ops/dev-stack.sh`:

```bash
ops/dev-stack.sh start
ops/dev-stack.sh temporal
ops/dev-stack.sh validate
ops/dev-stack.sh load --persona engineer
ops/dev-stack.sh smoke
ops/dev-stack.sh stop
CONFIRM_CLEAN=memoryhive ops/dev-stack.sh clean
```

Compose builds the `development` Docker stages. The backend uses Uvicorn reload, the frontend uses the Vite development server, and both source directories are bind-mounted.

## Automation

Goal 1 integration orchestration lives in `automation/`. It loads demo data,
runs the API smoke test, and reuses the web/mobile Playwright suites:

```bash
npm --prefix automation run doctor
npm --prefix automation run test -- --skip-mobile
npm --prefix automation run test:docker:cleanup
```

Use `BASE_URL=http://localhost:8000` or `--base-url` to target another running
backend. Add `--temporal` to exercise the Temporal Compose profile.

## Demo data

With the development stack running, seed four realistic demo libraries:

```bash
python3 seed_data.py
```

The script creates software-engineer, graduate-student, e-commerce, and home
lifestyle accounts. It is idempotent, so rerunning it does not duplicate items.
Use `python3 seed_data.py --help` to select one persona, target another API URL,
or preview the data with `--dry-run`.

## Local development

Start PostgreSQL, MinIO, and Redis-backed application services in Docker:

```bash
cp .env.example .env
docker compose up --detach db minio redis
```

Run the backend:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --requirement requirements.txt
export DATABASE_URL=postgresql+asyncpg://memoryhive:memoryhive123@localhost:5432/memoryhive
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin123
export MINIO_BUCKET=memoryhive-uploads
export JWT_SECRET_KEY=dev-secret-key-change-before-production
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 3000
```

## Production images

The final Dockerfile stages are production stages. They do not enable source reload or mount source directories.

```bash
docker build --target production --tag memoryhive-backend:local backend
docker build --target production --build-arg VITE_API_URL=/api/v1 --tag memoryhive-frontend:local frontend
```

The frontend production image serves static files on container port `80`. Its Nginx configuration proxies `/api/v1/*` to the Compose/Docker network service named `backend` on port `8000`. Deployments that run the services on different networks must update that upstream or provide an equivalent ingress route.

Production deployments must provide unique PostgreSQL, MinIO, JWT, and
encryption secrets. Production configuration fails closed when development
credentials, localhost origins, or missing Redis are detected.

## Production deployment

```bash
cp .env.production.example .env.production
chmod 600 .env.production
# Set real secrets, domain, ACME email, and immutable image tags.
docker compose --env-file .env.production -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
BASE_URL=https://memoryhive.example.com ops/smoke.sh
```

Caddy provides TLS and secure edge headers. The API adds request IDs,
structured JSON logs, Prometheus metrics, distributed rate limiting, readiness,
and security headers. See [the operations runbook](docs/OPERATIONS_RUNBOOK.md)
for monitoring, backup, restore, and rollback procedures.

## Temporal processing

The database-backed processing worker remains enabled by default. To test the
durable Temporal pipeline locally, run:

```bash
ops/dev-stack.sh temporal
```

This starts Temporal server/UI plus `temporal-worker` and `temporal-scheduler`.
With `TEMPORAL_ENABLED=true`, new captures are marked for analysis and scheduled
through Temporal. See [Temporal Processing Pipelines](docs/TEMPORAL_PIPELINES.md).

## Kubernetes build and deployment

Memoryhive includes a build/deployment toolchain based on the Goal 1 pipeline
blueprints. Generate image metadata, render manifests, and validate a profile:

```bash
make build-manifest IMAGE_VERSION=local
make k8s-generate K8S_ENV=local K8S_PROFILE=full
make k8s-validate K8S_ENV=local K8S_PROFILE=full
```

Tagged releases publish GHCR images with immutable `<version>-<short_sha>` tags
and upload `build/output/image-versions.json`. Manual Kubernetes deploys use
`.github/workflows/k8s-deploy.yml` and require a `KUBECONFIG_B64` secret for the
target GitHub environment. See [Kubernetes Deployment](docs/KUBERNETES_DEPLOYMENT.md).

## Mobile development and release

```bash
cd mobile
npm ci
npm run typecheck
npm test
npx expo start
```

The development client derives the API host from the web or Expo host and uses
port `8000`. Set `EXPO_PUBLIC_API_URL` only to override that default. Native
release profiles are defined in `mobile/eas.json`; store preparation and
physical-device checks are tracked in the release checklist.

Public store-support routes are served by the web app at `/privacy`,
`/account/delete`, and `/support`; deploy them on the production domain before
submitting mobile builds. Set `VITE_SUPPORT_EMAIL` on the web build to the
operator's real support address before release; the GitHub release workflow
expects the same value as a repository variable before publishing frontend
images.
Create a dedicated store-review account and set `STORE_REVIEW_ACCOUNT_EMAIL`
for the generated handoff packet; enter its temporary password directly in App
Store Connect and Play Console, not in source control.
For store handoff commands, provide public HTTPS release values through the
environment or an access-controlled production env file:
`EXPO_PUBLIC_API_URL` ending in `/api/v1`,
`EXPO_PUBLIC_PRIVACY_POLICY_URL` ending in `/privacy`,
`EXPO_PUBLIC_SUPPORT_URL` ending in `/support`, plus valid non-placeholder
`VITE_SUPPORT_EMAIL` and `STORE_REVIEW_ACCOUNT_EMAIL` addresses. Also set
`STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` so App Privacy
and Data safety drafts match production enrichment and telemetry behavior.

Store artwork and screenshot assets can be regenerated with
`npm --prefix mobile run store:assets` and
`npm --prefix mobile run store:screenshots`; build the submission packet with
`npm --prefix mobile run store:submission`, then check readiness with
`npm --prefix mobile run store:check`. CI runs the read-only
`store:submission:check` before `store:check:ci`, failing for missing or stale
generated packets and repository-owned defects while continuing to report
external release blockers.
For final handoff, run
`store:submission` and `store:check` with the same release environment so the
packet URLs, support email, and reviewer account match the checked config. Once
store-console and privacy forms are complete, record final evidence in
`mobile/store-assets/store-console-evidence.json` from the example template
before running the strict check.
Record EAS project, environment, signing, and submit setup evidence in
`mobile/builds/eas-release-evidence.json` after EAS setup is complete.
After setting the `EXPO_TOKEN` repository secret and committing the EAS
`projectId`, the manual `Mobile EAS Build` GitHub workflow can queue production
iOS, Android, or combined builds. It validates local release inputs, freezes
existing credentials, never auto-submits, and uploads the EAS JSON request.

```bash
npm --prefix mobile run store:submission -- --release-env-file .env.production
npm --prefix mobile run store:check -- --release-env-file .env.production --strict
```

## Configuration

| Variable | Used by | Description |
| --- | --- | --- |
| `POSTGRES_USER` | PostgreSQL, backend | Database user |
| `POSTGRES_PASSWORD` | PostgreSQL, backend | Database password |
| `POSTGRES_DB` | PostgreSQL, backend | Database name |
| `MINIO_ROOT_USER` | MinIO, backend | Local object-storage access key |
| `MINIO_ROOT_PASSWORD` | MinIO, backend | Local object-storage secret key |
| `MINIO_BUCKET` | Backend | Upload bucket name |
| `JWT_SECRET_KEY` | Backend | JWT signing secret |
| `JWT_ALGORITHM` | Backend | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | Access-token lifetime |
| `VITE_SUPPORT_EMAIL` | Frontend | Public support contact shown on compliance pages |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Backend | Refresh-token lifetime |
| `ENCRYPTION_KEY` | Backend | Application encryption key |
| `BACKUP_ROOT` | Backend, ops | Directory where backup snapshots are discovered or written |
| `BACKUP_RETENTION_DAYS` | Backend, ops | Backup retention window for cleanup and admin display |
| `ADMIN_BACKUP_COMMAND` | Backend | Optional admin-triggered backup command; leave blank to disable |
| `ADMIN_BACKUP_WORKING_DIR` | Backend | Optional working directory for `ADMIN_BACKUP_COMMAND` |
| `ADMIN_BACKUP_TIMEOUT_SECONDS` | Backend | Timeout for admin-triggered backup runs |
| `TEMPORAL_ENABLED` | Backend | Enables Temporal-backed analysis scheduling for new captures |
| `TEMPORAL_ADDRESS` | Temporal worker/scheduler | Temporal frontend address, such as `temporal:7233` |
| `TEMPORAL_NAMESPACE` | Temporal worker/scheduler | Temporal namespace for workflows |
| `TEMPORAL_TASK_QUEUE` | Temporal worker/scheduler | Task queue used by item analysis workflows |
| `TEMPORAL_SCHEDULER_POLL_SECONDS` | Temporal scheduler | Poll interval for pending item analysis |
| `TEMPORAL_SCHEDULER_BATCH_SIZE` | Temporal scheduler | Max pending items scheduled per poll |
| `CORS_ORIGINS` | Backend | JSON array of allowed browser origins |
| `VITE_API_URL` | Frontend | API v1 base URL; defaults to same-origin `/api/v1` in development |
| `VITE_PROXY_TARGET` | Frontend dev server | Backend target used by Vite's same-origin API proxy |
| `REDIS_URL` | Backend | Shared production rate-limit store |
| `ALLOWED_HOSTS` | Backend | JSON array of accepted HTTP hostnames |
| `EXPO_PUBLIC_API_URL` | Mobile | Device-reachable API v1 base URL |
| `EXPO_PUBLIC_PRIVACY_POLICY_URL` | Mobile | Public privacy policy URL shown from mobile Settings |
| `EXPO_PUBLIC_SUPPORT_URL` | Mobile | Public support URL shown from mobile Settings |
| `STORE_REVIEW_ACCOUNT_EMAIL` | Mobile store handoff | Dedicated reviewer account email; keep its password out of source control |
| `STORE_EXTERNAL_AI_PROCESSING` | Mobile store handoff | Declares whether production enrichment sends user content to no external processor, self-hosted AI, or third-party AI |
| `STORE_PRODUCTION_TELEMETRY` | Mobile store handoff | Declares production analytics/crash-reporting behavior for store privacy answers |

The canonical environment names are `JWT_SECRET_KEY` and `MINIO_BUCKET`. Legacy `SECRET_KEY` and `MINIO_BUCKET_NAME` names are not used by the Docker stack.

## Repository structure

```text
memoryhive/
|-- backend/             FastAPI application, Alembic migrations, and tests
|-- frontend/            React, TypeScript, Vite, and Nginx configuration
|-- mobile/              Expo iOS, Android, and offline synchronization client
|-- automation/          Seed, smoke, and Playwright integration orchestrator
|-- docs/                Product requirements and project status
|-- ops/                 Monitoring, smoke, backup, restore, and load tooling
|-- docker-compose.yml   Local development stack
|-- docker-compose.prod.yml Production stack with Caddy and Redis
|-- .env.example         Local environment template
\\-- README.md
```

## Product surface

- Capture links, screenshots, and text
- Search saved content and extracted text
- Organize content with tags, favorites, and archive state
- Offline-capable Expo mobile client with queued synchronization
- Durable link metadata and screenshot OCR processing worker

See `docs/MEMORYHIVE_REQUIREMENTS.md` for the product requirements,
`docs/REQUIREMENTS_TRACEABILITY.md` for implementation mapping, and
`docs/PROJECT_STATUS.md` for delivery status.
