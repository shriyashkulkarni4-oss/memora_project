# Memoryhive Implementation Plan

Last updated: 2026-09-05

## Objective

Deliver a production-ready Memoryhive implementation in controlled phases. The
responsive web application and core backend are completed first. Offline/mobile,
content processing, and production release work follow on the same contracts.

## Status Legend

- `TODO`: not started
- `IN PROGRESS`: active work
- `DONE`: implemented, verified, and committed
- `BLOCKED`: cannot proceed without an external decision or dependency

## Phase Summary

| Phase | Scope | Status | Commit |
|---|---|---|---|
| 0 | Restore a green development baseline | DONE | `phase-0-baseline` |
| 1 | Canonical product model and API contract | DONE | `phase-1-item-contract` |
| 2 | Core backend implementation | DONE | `phase-2-core-backend` |
| 3 | Production web UI | DONE | `phase-3-web-ui` |
| 4 | End-to-end UI/backend integration | DONE | `phase-4-web-integration` |
| 5 | Retrieval, privacy, and data lifecycle | DONE | `phase-5-retrieval-privacy` |
| 6 | Offline sync and mobile applications | DONE | `phase-6-offline-mobile` |
| 7 | OCR and content-processing pipeline | DONE | `phase-7-content-processing` |
| 8 | Production release readiness | DONE | `phase-8-production-release` |

## Product Decisions

- The canonical domain entity is an `Item`, with `link`, `screenshot`, and
  `text` variants.
- The responsive web client is the reference UI and API consumer. Native mobile
  clients follow after the core contract is stable.
- Categories remain optional and secondary. Tags and search are the primary
  organization and recall mechanisms.
- OCR is required for the publishable MVP. AI summaries and automatic tags are
  optional enhancements and must never block capture.
- Recall is in-app resurfacing for v1. Reminder notifications remain out of
  scope.
- Cloud storage is private per user. Server-side encryption at rest is the v1
  baseline; end-to-end encryption is a future architectural option.
- PostgreSQL and MinIO remain the backend stores. n8n/Ollama integrations are
  adapters around the core API rather than owners of application state.

## Phase 0: Green Baseline

Status: DONE

- [x] Remove or isolate obsolete duplicate backend modules.
- [x] Make the FastAPI application import and start successfully.
- [x] Align Python dependency declarations and configuration.
- [x] Repair the React lockfile and TypeScript build.
- [x] Add working frontend lint configuration.
- [x] Align Docker ports, service names, health checks, and environment names.
- [x] Add baseline backend and frontend tests.
- [x] Verify clean setup using documented commands.

Acceptance gate:

- `docker compose config` passes.
- Backend tests and application import pass.
- `npm ci`, frontend build, lint, and tests pass.
- The repository has no untracked generated files.

## Phase 1: Domain Model And API Contract

Status: DONE

- [x] Introduce user-owned `items`, `assets`, `tags`, and item-tag associations.
- [x] Support link, screenshot, and text item variants.
- [x] Add processing state, extracted text, source metadata, revisions, and soft
      deletion fields.
- [x] Use client-generated UUIDs and timezone-aware UTC timestamps.
- [x] Add migration coverage and database constraints.
- [x] Define stable `/api/v1` request, response, pagination, filter, and error
      contracts.
- [x] Generate or validate matching frontend API types.

Acceptance gate:

- A clean database migrates to head and back down in tests.
- OpenAPI describes all three item variants and consistent error responses.
- Ownership and uniqueness constraints are tested.

## Phase 2: Core Backend

Status: DONE

- [x] Harden registration, login, refresh, logout, and current-user flows.
- [x] Implement item CRUD, details, favorites, archive, and soft deletion.
- [x] Implement secure screenshot upload and private asset retrieval.
- [x] Implement user-owned category and tag CRUD.
- [x] Add cursor pagination and type/source/date/tag filters.
- [x] Add stats and processing-status endpoints.
- [x] Enforce ownership on every read and mutation.

Acceptance gate:

- API integration tests cover the complete core workflow.
- Cross-user access and foreign-key attachment attempts are rejected.
- Invalid uploads and malformed inputs return stable API errors.

## Phase 3: Production Web UI

Status: DONE

- [x] Establish the responsive app shell and accessible design primitives.
- [x] Build authentication, library, capture, search, detail, favorites, archive,
      categories/tags, and settings views.
- [x] Build URL, screenshot, and text capture modes with optional metadata.
- [x] Add complete loading, empty, validation, error, and processing states.
- [x] Verify mobile and desktop layouts visually.

Acceptance gate:

- All core screens render from contract-backed fixtures.
- Keyboard and screen-reader basics pass automated checks.
- Supported mobile and desktop viewport screenshots have no clipping or overlap.

## Phase 4: End-To-End Integration

Status: DONE

- [x] Replace all sample data with typed API-backed state.
- [x] Integrate authentication/session recovery and route protection.
- [x] Integrate capture, upload progress, search, filters, and item mutations.
- [x] Add optimistic actions with rollback and user-visible failures.
- [x] Add browser-level tests for primary workflows.

Acceptance gate:

- A user can register, capture each item type, find it, edit it, favorite it,
  archive it, restore it, and delete it through the UI.
- A page reload preserves server-backed state and session behavior.

## Phase 5: Retrieval, Privacy, And Data Lifecycle

Status: DONE

- [x] Add PostgreSQL full-text search and supporting indexes.
- [x] Search title, URL, raw text, extracted text, summaries, and tags.
- [x] Add duplicate-link detection and normalized source metadata.
- [x] Add user data export and account deletion.
- [x] Ensure asset cleanup is transactional and auditable.
- [x] Add performance and security regression tests.

Acceptance gate:

- Search/filter behavior is tested against a representative dataset.
- Export contains all user-owned data and account deletion removes it.

## Phase 6: Offline Sync And Mobile

Status: DONE

- [x] Implement a local item database and offline search.
- [x] Implement queued mutations, tombstones, revisions, and deterministic
      conflict handling.
- [x] Build the Expo iOS/Android client against shared contracts.
- [x] Add native share-sheet capture for links, text, and screenshots.
- [x] Verify reconnect and multi-device sync behavior.

Acceptance gate:

- Capture and search work in airplane mode.
- Queued changes sync without loss after reconnecting.

## Phase 7: OCR And Content Processing

Status: DONE

- [x] Add durable asynchronous processing jobs and retries.
- [x] Extract and normalize link metadata safely.
- [x] Run screenshot OCR and language detection.
- [x] Index extracted content for search.
- [x] Add optional n8n/Ollama summaries, classifications, and tag suggestions.
- [x] Surface processing progress and failures without blocking capture.

Acceptance gate:

- Screenshot text becomes searchable after processing.
- Processing failures are retryable and never lose captured content.

## Phase 8: Production Release

Status: DONE

- [x] Add CI/CD quality gates and production container builds.
- [x] Add TLS, secret management, rate limiting, and secure headers.
- [x] Add structured logging, metrics, health/readiness checks, and alerts.
- [x] Add PostgreSQL and MinIO backup/restore procedures.
- [x] Publish privacy policy, data-retention behavior, and operational runbooks.
- [x] Prepare web deployment and mobile store releases.

Acceptance gate:

- Staging deployment passes smoke, backup/restore, security, and performance
  checks.
- Release checklist and rollback procedure are documented and tested.

## Verification Log

| Date | Phase | Verification | Result |
|---|---|---|---|
| 2026-09-03 | Audit | Requirements and repository implementation review | Complete |
| 2026-09-03 | 0 | Backend pytest (4 tests), Ruff, and Black | Passed |
| 2026-09-03 | 0 | Frontend install, build, ESLint, Vitest, and npm audit | Passed |
| 2026-09-03 | 0 | Docker Compose configuration validation | Passed |
| 2026-09-03 | 0 | Docker runtime smoke test | Host Docker store corrupted after disk exhaustion; runtime test deferred |
| 2026-09-03 | 1 | Alembic clean database upgrade to head and downgrade to base | Passed on SQLite |
| 2026-09-03 | 1 | Item variant, OpenAPI, error envelope, ownership, and constraint tests | Passed |
| 2026-09-04 | 2 | Core API integration suite (11 total backend tests) | Passed |
| 2026-09-04 | 2 | PostgreSQL migrations and text capture smoke test | Passed |
| 2026-09-04 | 2 | MinIO screenshot upload and private download smoke test | Passed |
| 2026-09-04 | 2 | Full Compose image build | Docker Hub metadata request timed out; dependency services verified locally |
| 2026-09-04 | 3 | Vitest interaction tests and axe accessibility scan (3 tests) | Passed |
| 2026-09-04 | 3 | TypeScript production build and ESLint | Passed |
| 2026-09-04 | 3 | Playwright capture workflow at 1440x900 and iPhone 13 viewports | Passed |
| 2026-09-04 | 4 | Live PostgreSQL/MinIO browser workflow from registration through deletion | Passed |
| 2026-09-04 | 4 | Forced access-token refresh and session recovery on page reload | Passed |
| 2026-09-04 | 4 | Synthetic API failure with optimistic favorite rollback | Passed |
| 2026-09-04 | 4 | Backend tests, Ruff, Black; frontend build, lint, Vitest, and Playwright | Passed |
| 2026-09-04 | 5 | Migration 004 and PostgreSQL GIN search smoke test | Passed |
| 2026-09-04 | 5 | Search, URL deduplication, export, and deletion suite (13 backend tests total) | Passed |
| 2026-09-04 | 5 | Browser ZIP export, server search, and password-confirmed account deletion | Passed |
| 2026-09-04 | 5 | Lifecycle audit completed with no pending MinIO deletion jobs | Passed |
| 2026-09-05 | 6 | Backend change-feed/tombstone suite (14 backend tests total) | Passed |
| 2026-09-05 | 6 | Mobile TypeScript, ESLint, Vitest offline-sync suite, and Expo Doctor | Passed |
| 2026-09-05 | 6 | Expo static bundle and native share-intent configuration validation | Passed |
| 2026-09-05 | 6 | Live offline capture/search followed by reconnect sync to PostgreSQL | Passed |
| 2026-09-05 | 6 | Mobile UI at 1440x900 and 390x844 browser viewports | Passed |
| 2026-09-05 | 7 | Processing, SSRF, OCR normalization, and retry suite (21 backend tests total) | Passed |
| 2026-09-05 | 7 | PostgreSQL migration 005 and healthy API/worker containers | Passed |
| 2026-09-05 | 7 | Containerized Tesseract extraction followed by PostgreSQL search | Passed |
| 2026-09-05 | 7 | Live public-link metadata and readable-content extraction | Passed |
| 2026-09-05 | 7 | Web/mobile processing status, polling, errors, and retry controls | Passed |
| 2026-09-05 | 8 | Backend 26 tests, Ruff, Black; web/mobile full quality gates | Passed |
| 2026-09-05 | 8 | Clean production images, migrations, Caddy ingress, and service health | Passed |
| 2026-09-05 | 8 | Authenticated production capture/search/deletion smoke and security checks | Passed |
| 2026-09-05 | 8 | PostgreSQL/MinIO backup checksums, verification, and full isolated restore | Passed |
| 2026-09-05 | 8 | Prometheus target/rules and k6 10-user load test (p95 15 ms) | Passed |
