# Repository Guidelines

## Project Structure & Module Organization

Memoryhive combines FastAPI, Vite/React, and Expo. Backend code lives in `backend/app/`, Alembic migrations in `backend/migrations/`, and API tests in `backend/tests/`. Web source is in `frontend/src/`, split into `components/`, `hooks/`, `services/`, `store/`, `data/`, and `types/`; Playwright flows live in `frontend/e2e/`. Mobile routes use Expo Router in `mobile/app/`, shared logic lives in `mobile/src/`, tests in `mobile/tests/` and `mobile/e2e/`, and release assets in `mobile/store-assets/` and `mobile/builds/`. Delivery tooling is under `ops/`, `k8s/`, `build/`, `automation/`, and `docs/`.

## Build, Test, and Development Commands

- `cp .env.example .env && docker compose up --build`: start the local stack.
- `make health-local`: check backend, frontend, and dependency health.
- `cd backend && pip install -e '.[dev]' && alembic upgrade head`: install backend dev tools and run migrations.
- `cd backend && ruff check app tests && black --check app tests && pytest -q`: lint, format-check, and test the API.
- `npm --prefix frontend run dev|build|test|test:e2e`: run Vite, build, unit tests, or Playwright.
- `npm --prefix mobile run start|typecheck|lint|test|test:e2e:web`: run and validate Expo.
- `npm --prefix mobile run eas:build:preflight|store:assets|store:screenshots|store:submission|store:submission:check|store:check:ci`: validate EAS and store-release materials.

## Coding Style & Naming Conventions

Follow `.editorconfig`: UTF-8, spaces, two-space indentation, final newline, and trimmed trailing whitespace. TypeScript uses ESLint and single quotes. React components use `PascalCase`, hooks use `useThing`, tests use `*.test.ts` or `*.test.tsx`, and Expo routes follow filesystem names. Python uses Black/Ruff at 88 columns; modules, functions, and fixtures use `snake_case`.

## Testing Guidelines

Backend tests use pytest and belong in `backend/tests/test_*.py`. Frontend Vitest tests live as `*.test.ts(x)` under `frontend/src/`, with E2E specs in `frontend/e2e/*.e2e.ts`. Mobile unit and script tests live in `mobile/tests/*.test.ts` or `*.test.mjs`; E2E flows live in `mobile/e2e/*.e2e.ts`. Add focused regression tests for API contracts, auth, offline sync, release scripts, and changed user flows.

## Commit & Pull Request Guidelines

History mixes imperative subjects and Conventional Commit prefixes. Prefer `type: concise summary`, for example `fix: restore mobile sync retry`. Pull requests should include purpose, linked issue or goal, validation commands, screenshots for UI changes, and notes for migrations, environment variables, release impact, or deployments.

## Security & Agent-Specific Instructions

Use `.env.example` and `.env.production.example` as templates. Never commit JWT, database, Redis, MinIO, Temporal, Expo, or store credentials. Before agent edits, read `Knowledge.md` plus the relevant area guide, such as `backend/Knowledge.md`, `frontend/Knowledge.md`, `mobile/Knowledge.md`, or `ops/Knowledge.md`. After changing docs, commands, or layout, run `python3 scripts/generate_knowledge.py --check`.
