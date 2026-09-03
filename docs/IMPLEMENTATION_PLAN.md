# Memoryhive Implementation Plan

Last updated: 2026-09-03

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
| 1 | Canonical product model and API contract | TODO | Pending |
| 2 | Core backend implementation | TODO | Pending |
| 3 | Production web UI | TODO | Pending |
| 4 | End-to-end UI/backend integration | TODO | Pending |
| 5 | Retrieval, privacy, and data lifecycle | TODO | Pending |
| 6 | Offline sync and mobile applications | TODO | Pending |
| 7 | OCR and content-processing pipeline | TODO | Pending |
| 8 | Production release readiness | TODO | Pending |

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

Status: TODO

- [ ] Introduce user-owned `items`, `assets`, `tags`, and item-tag associations.
- [ ] Support link, screenshot, and text item variants.
- [ ] Add processing state, extracted text, source metadata, revisions, and soft
      deletion fields.
- [ ] Use client-generated UUIDs and timezone-aware UTC timestamps.
- [ ] Add migration coverage and database constraints.
- [ ] Define stable `/api/v1` request, response, pagination, filter, and error
      contracts.
- [ ] Generate or validate matching frontend API types.

Acceptance gate:

- A clean database migrates to head and back down in tests.
- OpenAPI describes all three item variants and consistent error responses.
- Ownership and uniqueness constraints are tested.

## Phase 2: Core Backend

Status: TODO

- [ ] Harden registration, login, refresh, logout, and current-user flows.
- [ ] Implement item CRUD, details, favorites, archive, and soft deletion.
- [ ] Implement secure screenshot upload and private asset retrieval.
- [ ] Implement user-owned category and tag CRUD.
- [ ] Add cursor pagination and type/source/date/tag filters.
- [ ] Add stats and processing-status endpoints.
- [ ] Enforce ownership on every read and mutation.

Acceptance gate:

- API integration tests cover the complete core workflow.
- Cross-user access and foreign-key attachment attempts are rejected.
- Invalid uploads and malformed inputs return stable API errors.

## Phase 3: Production Web UI

Status: TODO

- [ ] Establish the responsive app shell and accessible design primitives.
- [ ] Build authentication, library, capture, search, detail, favorites, archive,
      categories/tags, and settings views.
- [ ] Build URL, screenshot, and text capture modes with optional metadata.
- [ ] Add complete loading, empty, validation, error, and processing states.
- [ ] Verify mobile and desktop layouts visually.

Acceptance gate:

- All core screens render from contract-backed fixtures.
- Keyboard and screen-reader basics pass automated checks.
- Supported mobile and desktop viewport screenshots have no clipping or overlap.

## Phase 4: End-To-End Integration

Status: TODO

- [ ] Replace all sample data with typed API-backed state.
- [ ] Integrate authentication/session recovery and route protection.
- [ ] Integrate capture, upload progress, search, filters, and item mutations.
- [ ] Add optimistic actions with rollback and user-visible failures.
- [ ] Add browser-level tests for primary workflows.

Acceptance gate:

- A user can register, capture each item type, find it, edit it, favorite it,
  archive it, restore it, and delete it through the UI.
- A page reload preserves server-backed state and session behavior.

## Phase 5: Retrieval, Privacy, And Data Lifecycle

Status: TODO

- [ ] Add PostgreSQL full-text search and supporting indexes.
- [ ] Search title, URL, raw text, extracted text, summaries, and tags.
- [ ] Add duplicate-link detection and normalized source metadata.
- [ ] Add user data export and account deletion.
- [ ] Ensure asset cleanup is transactional and auditable.
- [ ] Add performance and security regression tests.

Acceptance gate:

- Search/filter behavior is tested against a representative dataset.
- Export contains all user-owned data and account deletion removes it.

## Phase 6: Offline Sync And Mobile

Status: TODO

- [ ] Implement a local item database and offline search.
- [ ] Implement queued mutations, tombstones, revisions, and deterministic
      conflict handling.
- [ ] Build the Expo iOS/Android client against shared contracts.
- [ ] Add native share-sheet capture for links, text, and screenshots.
- [ ] Verify reconnect and multi-device sync behavior.

Acceptance gate:

- Capture and search work in airplane mode.
- Queued changes sync without loss after reconnecting.

## Phase 7: OCR And Content Processing

Status: TODO

- [ ] Add durable asynchronous processing jobs and retries.
- [ ] Extract and normalize link metadata safely.
- [ ] Run screenshot OCR and language detection.
- [ ] Index extracted content for search.
- [ ] Add optional n8n/Ollama summaries, classifications, and tag suggestions.
- [ ] Surface processing progress and failures without blocking capture.

Acceptance gate:

- Screenshot text becomes searchable after processing.
- Processing failures are retryable and never lose captured content.

## Phase 8: Production Release

Status: TODO

- [ ] Add CI/CD quality gates and production container builds.
- [ ] Add TLS, secret management, rate limiting, and secure headers.
- [ ] Add structured logging, metrics, health/readiness checks, and alerts.
- [ ] Add PostgreSQL and MinIO backup/restore procedures.
- [ ] Publish privacy policy, data-retention behavior, and operational runbooks.
- [ ] Prepare web deployment and mobile store releases.

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
