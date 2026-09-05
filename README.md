# Memoryhive

Memoryhive is a mobile-first personal library for capturing links, screenshots, and text. This repository contains the React web client and FastAPI API, backed by PostgreSQL and MinIO.

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

## Local development

Start PostgreSQL and MinIO in Docker:

```bash
cp .env.example .env
docker compose up --detach db minio
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

Production deployments must provide unique PostgreSQL, MinIO, JWT, and encryption secrets. The values in `.env.example` are for local development only.

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

The canonical environment names are `JWT_SECRET_KEY` and `MINIO_BUCKET`. Legacy `SECRET_KEY` and `MINIO_BUCKET_NAME` names are not used by the Docker stack.

## Repository structure

```text
memoryhive/
|-- backend/             FastAPI application, Alembic migrations, and tests
|-- frontend/            React, TypeScript, Vite, and Nginx configuration
|-- docs/                Product requirements and project status
|-- docker-compose.yml   Local development stack
|-- .env.example         Local environment template
\\-- README.md
```

## Planned product surface

- Capture links, screenshots, and text
- Search saved content and extracted text
- Organize content with tags, favorites, and archive state
- Offline-capable Expo mobile client with queued synchronization
- Durable link metadata and screenshot OCR processing worker

See `docs/MEMORYHIVE_REQUIREMENTS.md` for product requirements and `docs/PROJECT_STATUS.md` for delivery status.
