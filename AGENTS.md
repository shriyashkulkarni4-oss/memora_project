# Repository Guidelines

## Project Structure & Module Organization

Memoryhive combines FastAPI, Vite/React, and Expo. Backend code lives in `cml-memoryhive-backend/app/`, Alembic migrations in `cml-memoryhive-backend/migrations/`, and API tests in `cml-memoryhive-backend/tests/`. Web source is in `cml-memoryhive-frontend/src/`, split into `components/`, `hooks/`, `services/`, `store/`, `data/`, and `types/`; Playwright flows live in `cml-memoryhive-frontend/e2e/`. Mobile routes use Expo Router in `cml-memoryhive-mobile/app/`, shared logic lives in `cml-memoryhive-mobile/src/`, tests in `cml-memoryhive-mobile/tests/` and `cml-memoryhive-mobile/e2e/`, and release assets in `cml-memoryhive-mobile/store-assets/` and `cml-memoryhive-mobile/builds/`. Delivery tooling is under `ops/`, `cml-memoryhive-deployments/`, `cml-memoryhive-build/build/`, `cml-memoryhive-automation/`, and `docs/`.

## Build, Test, and Development Commands

- `cp .env.example .env && docker compose up --build`: start the local stack.
- `make health-local`: check backend, frontend, and dependency health.
- `cd cml-memoryhive-backend && pip install -e '.[dev]' && alembic upgrade head`: install backend dev tools and run migrations.
- `cd cml-memoryhive-backend && ruff check app tests && black --check app tests && pytest -q`: lint, format-check, and test the API.
- `npm --prefix cml-memoryhive-frontend run dev|build|test|test:e2e`: run Vite, build, unit tests, or Playwright.
- `npm --prefix cml-memoryhive-mobile run start|typecheck|lint|test|test:e2e:web`: run and validate Expo.
- `npm --prefix cml-memoryhive-mobile run eas:build:preflight|store:assets|store:screenshots|store:submission|store:submission:check|store:check:ci`: validate EAS and store-release materials.

## Coding Style & Naming Conventions

Follow `.editorconfig`: UTF-8, spaces, two-space indentation, final newline, and trimmed trailing whitespace. TypeScript uses ESLint and single quotes. React components use `PascalCase`, hooks use `useThing`, tests use `*.test.ts` or `*.test.tsx`, and Expo routes follow filesystem names. Python uses Black/Ruff at 88 columns; modules, functions, and fixtures use `snake_case`.

## Testing Guidelines

Backend tests use pytest and belong in `cml-memoryhive-backend/tests/test_*.py`. Frontend Vitest tests live as `*.test.ts(x)` under `cml-memoryhive-frontend/src/`, with E2E specs in `cml-memoryhive-frontend/e2e/*.e2e.ts`. Mobile unit and script tests live in `cml-memoryhive-mobile/tests/*.test.ts` or `*.test.mjs`; E2E flows live in `cml-memoryhive-mobile/e2e/*.e2e.ts`. Add focused regression tests for API contracts, auth, offline sync, release scripts, and changed user flows.

## Commit & Pull Request Guidelines

History mixes imperative subjects and Conventional Commit prefixes. Prefer `type: concise summary`, for example `fix: restore mobile sync retry`. Pull requests should include purpose, linked issue or goal, validation commands, screenshots for UI changes, and notes for migrations, environment variables, release impact, or deployments.

## Security & Agent-Specific Instructions

Use `.env.example` and `.env.production.example` as templates. Never commit JWT, database, Redis, MinIO, Temporal, Expo, or store credentials. Before agent edits, read `Knowledge.md` plus the relevant area guide, such as `cml-memoryhive-backend/Knowledge.md`, `cml-memoryhive-frontend/Knowledge.md`, `cml-memoryhive-mobile/Knowledge.md`, or `ops/Knowledge.md`. After changing docs, commands, or layout, run `python3 scripts/generate_knowledge.py --check`.
