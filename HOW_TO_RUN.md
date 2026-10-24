# How to Run Memoryhive

This document outlines the requirements and step-by-step instructions to run the Memoryhive project locally.

## Prerequisites

Before you start, ensure you have the following installed on your system:
1. **Docker Engine & Docker Compose (v2 or newer):** Required to run services like PostgreSQL, MinIO, and Redis. On Windows, you can install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. **uv (Python Package Manager):** Required for backend dependency management.
   - Install via PowerShell (Windows): `irm https://astral.sh/uv/install.ps1 | iex`
3. **Node.js & npm:** Required for frontend and mobile app development.
4. **Make:** The `Makefile` is heavily used for running the project. 
   - Install on Windows via winget: `winget install GnuWin32.Make`

## Services Overview

The Memoryhive project consists of several services. Here is the contract of the primary services:

| Service | Development URL | Purpose |
| --- | --- | --- |
| **Frontend** | http://localhost:3000 | React + Vite frontend development server |
| **Backend** | http://localhost:8000 | FastAPI backend application |
| **API Docs** | http://localhost:8000/docs | OpenAPI / Swagger UI |
| **PostgreSQL** | localhost:5432 | Primary database |
| **MinIO API**| http://localhost:9000 | S3-compatible object storage |
| **MinIO Console**| http://localhost:9001 | MinIO admin UI |
| **Redis** | localhost:6379 | Used for distributed rate limiting |
| **Mobile App** | http://localhost:8083 | Expo development preview |
| **Temporal UI** | http://localhost:8233 | (Optional) Temporal processing pipelines UI |

## Step-by-Step Instructions

### 1. Setup Environment Variables
Start by copying the example environment files for local development.

```bash
cp .env.example .env
```

### 2. Start Infrastructure (Database, Storage, Cache)
If you want to run the application components (Frontend & Backend) directly on your machine but use Docker for the databases, start the infrastructure using Make:

```bash
make -C cml-memoryhive-build up PROFILE=infra
```

Alternatively, you can run the entire stack (Backend + Frontend + Infra) entirely in Docker:
```bash
make -C cml-memoryhive-build up PROFILE=full
```

### 3. Run the Backend Locally
If you chose to run only the infrastructure in Docker (`PROFILE=infra`), open a new terminal and run the FastAPI backend:

```bash
cd cml-memoryhive-backend

# Install dependencies and sync environment
uv sync --extra dev --locked

# Setup environment variables needed for backend
export DATABASE_URL=postgresql+asyncpg://memoryhive:memoryhive123@localhost:5432/memoryhive
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin123
export MINIO_BUCKET=memoryhive-uploads
export JWT_SECRET_KEY=dev-secret-key-change-before-production

# Run database migrations
uv run alembic upgrade head

# Start the server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Run the Frontend Locally
In another terminal, run the React frontend:

```bash
cd cml-memoryhive-frontend

# Install dependencies
npm ci

# Start the development server
npm run dev -- --host 0.0.0.0 --port 3000
```

### 5. Run the Mobile Client Locally (Optional)
If you want to develop the React Native (Expo) mobile app, run it in another terminal:

```bash
cd cml-memoryhive-mobile

# Install dependencies
npm ci

# Start the Expo development server
npx expo start
```

### 6. Seed Demo Data (Optional)
You can populate your local database with mock users and demo data. Ensure the backend is already running and ready, then run the seed script from the root directory:

```bash
uv run python seed_data.py
```

### 7. Run Automated Tests
You can run the suite of tests across the stack using the goal-2-test make command.

```bash
make goal-2-test
```
For individual tests, you can run `uv run pytest` inside `cml-memoryhive-backend` or `npm test` inside `cml-memoryhive-frontend` and `cml-memoryhive-mobile`.
