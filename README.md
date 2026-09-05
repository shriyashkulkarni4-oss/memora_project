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

Compose builds the `development` Docker stages. The backend uses Uvicorn reload, the frontend uses the Vite development server, and both source directories are bind-mounted.

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
VITE_API_URL=http://localhost:8000/api/v1 npm run dev -- --host 0.0.0.0 --port 3000
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

## Mobile development and release

```bash
cd mobile
npm ci
npm run typecheck
npm test
npx expo start
```

Set `EXPO_PUBLIC_API_URL` to a device-reachable `/api/v1` URL. Native release
profiles are defined in `mobile/eas.json`; store preparation and physical-device
checks are tracked in [the release checklist](docs/RELEASE_CHECKLIST.md).

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
| `REFRESH_TOKEN_EXPIRE_DAYS` | Backend | Refresh-token lifetime |
| `ENCRYPTION_KEY` | Backend | Application encryption key |
| `CORS_ORIGINS` | Backend | JSON array of allowed browser origins |
| `VITE_API_URL` | Frontend | Browser-reachable API v1 base URL |
| `REDIS_URL` | Backend | Shared production rate-limit store |
| `ALLOWED_HOSTS` | Backend | JSON array of accepted HTTP hostnames |
| `EXPO_PUBLIC_API_URL` | Mobile | Device-reachable API v1 base URL |

The canonical environment names are `JWT_SECRET_KEY` and `MINIO_BUCKET`. Legacy `SECRET_KEY` and `MINIO_BUCKET_NAME` names are not used by the Docker stack.

## Repository structure

```text
memoryhive/
|-- backend/             FastAPI application, Alembic migrations, and tests
|-- frontend/            React, TypeScript, Vite, and Nginx configuration
|-- mobile/              Expo iOS, Android, and offline synchronization client
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
