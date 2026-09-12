# Role 
Consider yourself as a Full Stack Architect Specialized in React, Python, AI, Async processing etc and Implement things with best of your knowledge and abilities

# Current Status and Handoff

**Goal 1 is not fully complete.** Repository implementation is validated with
zero repository release blockers; 16 external mobile-release blockers remain.
Start with [`Goal Status/README.md`](Goal%20Status/README.md) for the concise
summary, numbered requirement matrix, validation evidence, owners, and exact
continuation sequence.

# Run Instructions 
1) Run this with Parallel Agents if needed.

2) If you need any decision, go with `YES` for now, but document those decisions at /Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-memoryhive/docs/DECISIONS-GOAL-1.MD

3) Do not wait for my approval, take your Judgement call 

# WebApp Changes 

1) In the library, we have numbers of Items on top with Favorites etc. This Section, the items should work as filters. If I click, the bottom list gets filtered out. 

2) When we filter or group of filters, lets introduce a pattern of showing the Pills with X Buttons, so if I click on X, the Filter is removed and at same time the Pill is removed too. Implement this pills as common compoent and lets use it in all filters. 

3) We need Pills etc everywhere we are doing the Filters. 

4) The Title of the Card is clicable..Better to Implement a Show Details Button. And provide that too. When user Hover on the Title, or this Button, it should highlight and show.

5) Delete Button should have a the Confirmation popup, allow user to decide if they want to continue or cancel. 

6) On Cards, the Favorite Button Not working.  Or. Atleast it does not show up when we click on it.  Validate and fix

7) Implement a way for users to tag, untag a item. Cards favorite/UnFavorite not working in Any view. Also implement a Confirmation Dialog here. 

8) Archieve, unArchive - Lets implement those options.  There is no easy way to Archive and unArchive. Again Implement Confirmation Dialogs. 

9) IN General, all Delete Operation should be supported with Confirmation Dialog. Validate and add. 

11) From Organize, click to a Tag and route user to the Library with filters applied. Tags should be a filter on the Library too. Introduce all tags to be clicable. 

12) Settings Should have a way to change password too. Edit password should be supported with Confirm dialogs. And if user change password, then force logoff user with message that password changed successfully.

13) Synced on Left Nav -> Should show the date when it synced. 

14) LocalStorage etc.. plan it well. Logoff, cleans all localstorage, so login/logoff experiance should be good and crisp. 

15) Implement User Idle scenario and refresh the view after every 1 min, if screen is idle.  If Screen remains idle for 10+ mins, then logoff user with a message. 

16) Logoff Button not clearly visible. Better to implement a Button visible.. 

# Mobile App Changes

1) Mobile Features should be similar to the WebApp. Review all Features and Implement the ones which are missing. Also refer to the suggestions I gave for webapp. 

2) Item Details should be similar to the WebApp. 

3) In Capture or Edit, the Tags needs to be AutoSelect based on Search. When user selects a Tag, it shows up as Pill with X button, so that user get chance to Add / edit more tags etc 

4) Settings should align to the WebApp too 

5) Library and Search need to get better and aligned with WebApp, searching is key.. 

6) Organize Feature from WebApp is missing in webApp

7) We need our Mobile App, to be implemented for Android and IOS too.  Check readyness, and tell us what needs to be done. 

8) Validate Build for the Mobile App. Write the MD files on how to Build and test the Android and IOS Apps.

9) Does our Mobile App ready to publish on AppStore, Write a MD File talking about readyness and GAPs.. 

10) Generate all docs etc needed to publish apps to AppStore.. whats missing. 


# WebApp as Admin Persona 

1) We do not have a view for Admin Users. E.g. If I am a admin who is managing this app and all users etc.  I should have a admin level view of everyting. 

2) Implement Personas in the system, Admin, User for now.  

3) Admin User needs a lot of dashboards, and graphs etc. Think about all possible usecases Admin needs to know about and implement thoe workflows. Make sure to document it

4) As a Admin user, I should have a way to enable/disable access for Users in system. Also I should be able to delete the Users from and all their data etc. 

5) Admins manage this system so think about it overall.


# Temporal Pipelines App for offline Data Processing 

1) We need to identify usecases which can run in background for user actions.  Design a new docker and Temporal based app to support these operations. Lets define this in Python typiclaly, so all tasks would be implemented in python code 

2) We need a way, to Pick the Items from user Libraries and Peform analyssi and 
    2.1) For URLs, Generate the AI Analsis of those Items. 
    2.2) For Images, Run the OCR on it and generate the summary
    2.3) For Text, Run AI Analysis and prepare the content summary  

3) Add the column etc in Item DB, to maintain data about if Items is analyzed or not. Updating of this would happen offline and Temporal app tasks would update it. 

4) Think what else this app can do overall. 

# DB and Data Seeing

2) Implement Data Seeding Mechanism to validate these all things 

3) Implement Scripts to Start, Stop, Clean DB, Load DB with Mock Data etc.. 

4) Implement Database backup mechanism.  Admin should have a view and a way to backup whole DB 


## Testing 

1) Test each of these apps to make sure they work in realtime on my docker containers 

2) Test WebApp, and Mobile App Both.  Check if we want to implement PlayWrite based Automation to Test UI workflows. Implement this as a Separate App under the project. 

3) Implement Scripts in the App, to 
   3.1) Run things on Docker Container 
   3.2) Validtae if things are running
   3.3) Use the Scripting to Load Data, Cleanup Data
   3.4) Automation should load mock data, validate high level scenarios and then tear down when closing 

4) Improvise wheverever you can. 


# Kubernetes Based Deployments 

1) Implement Build Pipeline, as suggested in the template /Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-zestro/docs/templates/BUILD_PIPELINE_BLUEPRINT.md

2) Implement the K8S Build and Deploy Pipeline as suggested in the Template /Users/mahesh-kulkarni/projects/coding-monkey-labs-client-projects/cml-zestro/docs/templates/K8S_DEPLOYMENT_BLUEPRINT.md

# KBS
1) Generate Agents.md and wiring for the Claude, Codex, Antigravity to start using Knowledge.md before making any changes
2) Generate Knowledge.MD Files in every Sub-Project and wire it with the Harness from Step 1
3) Implement Scripts to update/re-generate Knowledge.md when run 


---

# Implementation Results

## 2026-09-06 - Web Library Filter and Card Actions Slice

Status: Completed and validated for the web app.

Implemented:
- Added reusable `FilterPills` for active filter display and one-click removal.
- Added reusable `ConfirmDialog` and replaced native/no-confirm flows for item favorite, archive, restore, delete, category delete, and tag delete entry points touched in this slice.
- Added `TagPicker` with search suggestions, selected tag pills, and X removal for capture and item edit flows.
- Made library summary counts clickable filters for saved, favorites, processing, and archived items.
- Added URL-backed library filters for search query, type, category, tag, and summary state so filters are linkable.
- Made item card tags clickable filters and added a visible Details action while keeping title navigation.
- Made Organize categories and tags clickable routes into Library with filters applied.
- Updated item detail editing to support tag add/remove and linked detail tags back to Library filters.
- Added unit coverage for summary filter pills and card favorite confirmation.

Validated:
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- Backend admin/persona foundation.
- Password change and session hardening.
- Mobile parity for library filters, tags, details, settings, and organize.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Admin Persona Foundation Slice

Status: Completed and validated for backend API plus web admin surface.

Implemented:
- Added `admin` and `user` personas through a new `users.role` field and Alembic migration `006_user_roles.py`.
- Added development first-user admin bootstrap and production `ADMIN_BOOTSTRAP_EMAILS` configuration.
- Added admin authentication dependency that returns `403` for non-admin users.
- Added `/api/v1/admin/dashboard` for user, item, asset, storage, and processing queue counts.
- Added `/api/v1/admin/users` list with per-user item, asset, and storage totals.
- Added admin user enable/disable, promote/demote, and delete endpoints with self-disable/self-demote/self-delete protection.
- Extracted shared account deletion lifecycle service so user self-delete and admin-delete both create cleanup audit records and remove stored assets.
- Added backend tests for admin bootstrap, non-admin rejection, dashboard counts, access disabling, login blocking, re-enable, and admin deletion cleanup.
- Added web Admin route, admin-only nav entry, dashboard metrics, operational bars, user table, and confirmation dialogs for admin actions.
- Updated frontend API and user types for `role` and admin contracts.

Validated:
- `cd backend && ./.venv/bin/ruff check app tests`
- `cd backend && ./.venv/bin/black --check app tests`
- `cd backend && ./.venv/bin/pytest -q`
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- Password change and forced logout/session hardening.
- Mobile parity for filters, tags, details, settings, and organize.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Password Change and Session Hardening Slice

Status: Completed and validated for backend API plus web settings flow.

Implemented:
- Added `session_version` and `password_changed_at` user metadata with Alembic migration `007_password_session_hardening.py`.
- Added `POST /api/v1/auth/change-password` with current-password verification, new-password validation, same-password rejection, password hash update, refresh-token revocation, and session-version increment.
- Hardened authenticated dependencies so access tokens from older session versions are rejected after password changes.
- Added backend tests proving stale access tokens, old refresh tokens, and old passwords fail after password change while the new password works.
- Updated the web API client with `changePassword` and local session cleanup that clears the `memoryhive.*` localStorage namespace.
- Added a Settings > Security change-password flow with confirmation dialog.
- Forced the web user to the login page after password change with a success message.

Validated:
- `cd backend && ./.venv/bin/ruff check app tests`
- `cd backend && ./.venv/bin/black --check app tests`
- `cd backend && ./.venv/bin/pytest -q`
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- Idle refresh/logout behavior on web and mobile.
- Mobile parity for filters, tags, item details, settings, and organize.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Web Idle and Session Cleanup Slice

Status: Completed and validated for the web app.

Implemented:
- Made web logout server revocation best-effort while guaranteeing local token cleanup and auth state reset.
- Added app-level handling for `memoryhive:session-expired` so expired sessions clear in-memory library data and redirect to login with a message.
- Added idle tracking in `AppShell`: after 60 seconds of inactivity the library refreshes; after 10 minutes of inactivity the user is signed out with a login-page message.
- Added regression tests for session-expired cleanup and idle logout messaging.

Validated:
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- Mobile forced logout/session-expired cleanup and settings password-change parity.
- Mobile library/search/tag/filter parity.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Mobile Session and Password Settings Slice

Status: Completed and validated for the Expo mobile client.

Implemented:
- Added mobile API support for `POST /auth/change-password`.
- Made mobile logout best-effort for server revocation while still clearing local credentials.
- Added a single mobile forced-logout path that clears SecureStore/localStorage credentials, SQLite items/mutations/metadata, in-memory items, auth state, and routes to login with a message.
- Added handling for `401` sync failures and failed session restore so expired sessions clear local user data instead of remaining as sync errors.
- Added mobile idle handling in the root app provider: idle sessions sync every 60 seconds and sign out after 10 minutes.
- Added Settings > Security password-change flow with native confirmation and forced login after success.
- Added login-page notice support for forced logout and password-change success messages.
- Updated mobile `User` type to accept backend `role`.

Validated:
- `cd mobile && npm run typecheck`
- `cd mobile && npm run lint`
- `cd mobile && npm test`

Next planned slices:
- Mobile library/search/tag/filter parity and item detail parity.
- Mobile build/readiness documentation for iOS and Android.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Mobile Library, Search, and Detail Parity Slice

Status: Completed and validated for the Expo mobile client.

Implemented:
- Added shared mobile item filtering helpers for search query, item type, summary state, and tag filtering.
- Added reusable mobile `FilterPills` and `TagPicker` components with selected tag pills and X removal.
- Updated Home and Search with summary count filters, type filters, active filter pills, tag rails, and archived visibility.
- Updated Capture to use tag suggestions and selected tag pills.
- Updated Item Detail with edit mode for title, notes, and tags; favorite, archive, restore, and delete confirmations; and clickable tag navigation back to filtered Home.
- Updated mobile refresh paths to include archived records where filtered views need them.

Validated:
- `cd mobile && npm run typecheck`
- `cd mobile && npm run lint`
- `cd mobile && npm test`

Next planned slices:
- Mobile account export, account deletion, and privacy policy controls.
- Mobile build/readiness documentation for iOS and Android.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Mobile Account Privacy and Deletion Slice

Status: Completed and validated for the Expo mobile client.

Implemented:
- Added mobile account export support through the backend `/account/export` endpoint with access-token refresh retry.
- Added native export handoff via `expo-sharing`; web preview falls back to browser ZIP download.
- Added mobile account deletion through the backend `/account` endpoint with password plus `DELETE` confirmation and native destructive confirmation.
- Routed successful account deletion through the existing forced logout path so credentials, SQLite rows, in-memory items, and navigation are cleared consistently.
- Added a Settings privacy policy action backed by configurable `EXPO_PUBLIC_PRIVACY_POLICY_URL`, with `/privacy` derived from the API origin as fallback.
- Documented mobile account controls and privacy URL configuration in `mobile/README.md`, `.env.example`, and `.env.production.example`.
- Added unit coverage for export filename parsing and privacy URL resolution.

Validated:
- `cd mobile && npm run typecheck`
- `cd mobile && npm run lint`
- `cd mobile && npm test`

Next planned slices:
- Active iOS and Android build/test documentation.
- Mobile App Store and Play Store readiness gap documentation.
- Store metadata, privacy, and data-safety documentation.

## 2026-09-06 - Mobile Build and Store Readiness Documentation Slice

Status: Completed and validated for active Goal 1 documentation.

Implemented:
- Created `docs/GOAL-1/MOBILE_IOS_BUILD_TEST.md` with iOS prerequisites, EAS build commands, physical-device test checklist, and submit steps.
- Created `docs/GOAL-1/MOBILE_ANDROID_BUILD_TEST.md` with Android prerequisites, EAS build commands, target API verification, permission verification, and submit steps.
- Created `docs/GOAL-1/MOBILE_APP_STORE_READINESS.md` with a current not-ready verdict, completed items, blocking gaps, and recommended order.
- Created `docs/GOAL-1/MOBILE_STORE_METADATA.md` with draft store copy, keywords, screenshot plan, review notes, and missing assets.
- Created `docs/GOAL-1/MOBILE_PRIVACY_DATA_SAFETY.md` with Apple App Privacy and Google Data safety engineering drafts.
- Verified current Expo, Apple, and Google guidance from official sources before writing store/readiness docs.
- Added Android `blockedPermissions` for `android.permission.RECORD_AUDIO` because Memoryhive does not record audio.

Validated:
- `cd mobile && npm run typecheck`
- `cd mobile && npm run lint`
- `cd mobile && npm test`
- `cd mobile && npx expo config --type public`
- `find docs/GOAL-1 -maxdepth 1 -type f -print | sort`

Next planned slices:
- Public privacy and web account deletion pages.
- EAS initialization and production mobile build artifacts.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Public Privacy and Account Deletion Pages Slice

Status: Completed and validated for the web app.

Implemented:
- Added public `/privacy` route with Memoryhive-specific data collection, use, security, export, deletion, and contact information.
- Added public `/account/delete` route with web deletion instructions for users who no longer have the mobile app installed.
- Linked privacy policy and account deletion pages from login/register.
- Linked privacy policy and web deletion instructions from authenticated Settings.
- Updated mobile readiness, metadata, privacy/data-safety docs, root README, and environment examples to reflect the new production URLs and remaining deployment/contact gaps.
- Added frontend unit coverage for both public compliance pages.

Validated:
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- EAS initialization and production mobile build artifacts.
- Store assets/screenshots and real operator support URL.
- Processing/admin/ops visibility and backup workflow expansion.

## 2026-09-06 - Mobile Organize Tab Slice

Status: Completed and validated for the Expo mobile client.

Implemented:
- Added a mobile Organize tab to the authenticated tab bar.
- Added `summarizeOrganization` helper for active, archived, favorite, processing, type, and tag counts.
- Added Organize status tiles that route to Home with the matching summary filter applied.
- Added type rows that route to Home with the matching item-type filter applied.
- Added tag rows that route to Home with the matching tag filter applied.
- Scoped mobile Organize to item-backed local data because categories are not currently synced into the mobile SQLite model.
- Added unit coverage for organization summary counts, tag normalization, sorting, and archived-tag exclusion.

Validated:
- `cd mobile && npm run typecheck`
- `cd mobile && npm run lint`
- `cd mobile && npm test`

Next planned slices:
- EAS initialization and production mobile build artifacts.
- Processing/admin/ops visibility and backup workflow expansion.

Historical follow-up completed later:
- Mobile category/tag management parity was implemented in the Mobile Category Management Parity Slice.

## 2026-09-06 - Admin Backup Visibility and Control Slice

Status: Completed and validated for backend API plus web admin surface.

Implemented:
- Added backend backup service helpers to inspect backup directories for PostgreSQL dump, MinIO mirror directory, checksums, size, and created time.
- Added admin-only `GET /api/v1/admin/backup` status endpoint.
- Added admin-only `POST /api/v1/admin/backup/run` endpoint that runs a configured backup command with timeout and fail-closed behavior.
- Added configuration for `BACKUP_ROOT`, `BACKUP_RETENTION_DAYS`, `ADMIN_BACKUP_COMMAND`, `ADMIN_BACKUP_WORKING_DIR`, and `ADMIN_BACKUP_TIMEOUT_SECONDS`.
- Added backend tests for disabled backup execution and successful configured backup execution.
- Added web Admin backup panel with latest backup, retention, visible command state, recent backup health flags, and confirmation-protected run action.
- Updated `README.md`, `.env.example`, `.env.production.example`, and `docs/OPERATIONS_RUNBOOK.md` for admin-triggered backup configuration.

Validated:
- `cd backend && ./.venv/bin/ruff check app tests`
- `cd backend && ./.venv/bin/black --check app tests`
- `cd backend && ./.venv/bin/pytest -q`
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- Data operations scripts for start/stop/clean/load workflows.
- Processing/admin visibility for Temporal-style background processing.
- Kubernetes build/deploy pipeline templates.

## 2026-09-06 - Development Stack Operations Script Slice

Status: Completed and validated for local script syntax and help output.

Implemented:
- Added `ops/dev-stack.sh` as a single local Docker development wrapper.
- Supports `start`, `stop`, `restart`, `status`, `logs`, `migrate`, `validate`, `load`, `smoke`, and `clean`.
- Creates `.env` from `.env.example` when needed.
- Reuses existing `seed_data.py` for demo/mock data loading.
- Reuses existing `ops/smoke.sh` for high-level API validation.
- Requires `CONFIRM_CLEAN=memoryhive` before deleting Docker volumes.
- Documented the workflow in `README.md`.

Validated:
- `sh -n ops/dev-stack.sh`
- `ops/dev-stack.sh --help`

Next planned slices:
- Processing/admin visibility for Temporal-style background processing.
- Kubernetes build/deploy pipeline templates.
- KBS Knowledge.md generation and agent wiring.

## 2026-09-06 - KBS Knowledge Harness Slice

Status: Completed and validated for generated documentation and harness wiring.

Implemented:
- Added `scripts/generate_knowledge.py` to generate deterministic Knowledge docs.
- Generated root `Knowledge.md`.
- Generated sub-project Knowledge docs for `backend/`, `frontend/`, `mobile/`, `ops/`, and `docs/`.
- Updated `AGENTS.md` with a Knowledge Harness section while keeping the contributor guide concise.
- Added `CLAUDE.md`, `CODEX.md`, and `ANTIGRAVITY.md` adapters that direct agents to read `AGENTS.md`, root `Knowledge.md`, and relevant sub-project Knowledge docs before changes.
- Added `--check` mode to detect stale generated Knowledge docs in local or CI workflows.

Validated:
- `python3 -m py_compile scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `wc -w AGENTS.md`

Next planned slices:
- Processing/admin visibility for Temporal-style background processing.
- Kubernetes build/deploy pipeline templates.
- EAS initialization and production mobile build artifacts.

## 2026-09-06 - Admin Processing Queue Visibility Slice

Status: Completed and validated for backend API plus web admin surface.

Implemented:
- Added admin-only `GET /api/v1/admin/processing/jobs` with status filtering, pagination, item context, user email, attempts, schedule, lock, error, and completion timestamps.
- Added admin-only `POST /api/v1/admin/processing/jobs/{job_id}/retry` for failed jobs.
- Kept retry history by creating a new pending `ProcessingJob` through the existing worker retry helper instead of mutating the failed job.
- Added backend integration coverage for non-admin rejection, failed-job queue listing, retry success, and duplicate retry conflict.
- Added a DB-aware test fixture for API tests that need direct setup while preserving the existing `api_client` fixture contract.
- Added a web Admin Processing Queue panel with recent jobs, status badges, attempt counts, next-attempt time, error display, and confirmation-protected retry.
- Documented processing queue operations in `docs/OPERATIONS_RUNBOOK.md`.

Validated:
- `cd backend && ./.venv/bin/ruff check app tests`
- `cd backend && ./.venv/bin/black --check app tests`
- `cd backend && ./.venv/bin/pytest -q`
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`

Next planned slices:
- Temporal deployment design and container wiring for durable offline processing.
- Kubernetes build/deploy pipeline templates.
- EAS initialization and production mobile build artifacts.

## 2026-09-06 - Kubernetes Build and Deploy Pipeline Slice

Status: Completed and validated for repository pipeline assets and rendered local manifests.

Implemented:
- Added `build/services.json` as the source of truth for backend/frontend image build contexts, production targets, build args, and runtime image reuse.
- Added `build/scripts/generate_image_manifest.py` to generate the deployment handoff artifact `build/output/image-versions.json`.
- Added `build/scripts/build_images.py` for consistent local or push-capable Docker buildx commands with `<version>-<short_sha>`, `<version>`, and `latest` tags.
- Added `k8s/config/environments.json`, `k8s/config/profiles.json`, and `k8s/image-versions.json` for environment/profile/image pinning.
- Added `k8s/scripts/manage.py` with `generate`, `validate`, `apply`, `upgrade`, `status`, `rollback`, and guarded `delete` commands.
- Generated Kubernetes manifests for namespace, quota, limits, config, secrets placeholders, PostgreSQL, Redis, MinIO, backend, worker, frontend, ingress, and network policies.
- Added `health_checker/health_check.py` for local, Docker, and Kubernetes health checks from one service registry.
- Added root `Makefile` targets for build manifest, image build, health, K8s generate, validate, status, and upgrade.
- Updated `.github/workflows/ci.yml` to validate deployment assets.
- Updated `.github/workflows/release.yml` to publish immutable GHCR tags and upload an image-version manifest artifact.
- Added `.github/workflows/k8s-deploy.yml` for manual validate/apply/upgrade/status workflows using GitHub environments and `KUBECONFIG_B64`.
- Added `docs/KUBERNETES_DEPLOYMENT.md`, updated `README.md`, and regenerated Knowledge docs for the new build/K8s/health surfaces.

Validated:
- `python3 -m py_compile build/scripts/*.py k8s/scripts/*.py health_checker/*.py scripts/generate_knowledge.py`
- `python3 build/scripts/generate_image_manifest.py --version test --sha 1234567890abcdef --output /tmp/memoryhive-image-versions.json`
- `python3 build/scripts/build_images.py --version test --sha 1234567890abcdef --dry-run`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s validate local full`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s validate local infra`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s validate staging app-only`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s validate local full --kubectl-dry-run`
- Python/PyYAML parse of `.github/workflows/*.yml` and rendered `local/full` manifests
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Next planned slices:
- Temporal deployment design and container wiring for durable offline processing.
- EAS initialization and production mobile build artifacts.
- Store assets/screenshots and production support/contact metadata.

## 2026-09-06 - Temporal Analysis Pipeline Slice

Status: Completed and validated for backend analysis state, Temporal worker/scheduler wiring, Docker Compose, and Kubernetes profile rendering.

Implemented:
- Added item analysis state with `analysis_status`, `analysis_error`, `analysis_version`, and analysis timestamps through Alembic migration `008_item_analysis_state.py`.
- Added Temporal Python SDK dependency and a Python pipeline under `backend/app/temporal_pipeline/` with workflow, activity, worker, scheduler, and idempotent workflow IDs.
- Added shared analysis helpers that mark items analyzing/analyzed/failed, guard stale `analysis_version` requests, preserve user-entered title/description, and store analysis metadata.
- Extended content processing to analyze text captures, run optional Ollama/n8n enrichment, and create deterministic fallback summaries when external AI is not configured.
- Marked new and content-edited items as pending analysis; surfaced pending/failed analysis counts in item stats, admin dashboard, web types, mobile types, fixtures, and local mobile updates.
- Wired a Docker Compose `temporal` profile with Temporal PostgreSQL, Temporal server, Temporal UI, `temporal-worker`, and `temporal-scheduler`.
- Added production Compose worker/scheduler services for deployments that point at an external Temporal cluster.
- Added a Kubernetes `temporal` profile for `temporal-worker` and `temporal-scheduler`, including config rendering, upgrade support, rollback choices, CI validation, and manual deploy workflow selection.
- Updated the legacy processing worker so default non-Temporal processing also updates the new analysis state instead of leaving completed items falsely pending.
- Documented Temporal operations in `docs/TEMPORAL_PIPELINES.md`, `README.md`, and `docs/OPERATIONS_RUNBOOK.md`.

Validated:
- `cd backend && ./.venv/bin/ruff check app tests`
- `cd backend && ./.venv/bin/black --check app tests`
- `cd backend && ./.venv/bin/pytest -q`
- `cd backend && DATABASE_URL=sqlite+aiosqlite:////tmp/memoryhive-alembic-goal1-<timestamp>.db ./.venv/bin/alembic upgrade head`
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- `cd mobile && npm run typecheck`
- `cd mobile && npm run lint`
- `cd mobile && npm test`
- `docker compose --env-file .env.example -f docker-compose.yml config --quiet`
- `docker compose --env-file .env.example -f docker-compose.yml --profile temporal config --quiet`
- `docker compose --env-file .env.production.example -f docker-compose.prod.yml config --quiet`
- `docker compose --env-file .env.production.example -f docker-compose.prod.yml --profile temporal config --quiet`
- `sh -n ops/dev-stack.sh`
- `python3 -m py_compile k8s/scripts/manage.py build/scripts/build_images.py build/scripts/generate_image_manifest.py health_checker/health_check.py scripts/generate_knowledge.py`
- `cd backend && ./.venv/bin/python -m py_compile app/services/analysis.py app/temporal_pipeline/*.py`
- `python3 build/scripts/generate_image_manifest.py --version temporal-test --sha 1234567890abcdef --output /tmp/memoryhive-temporal-image-versions.json`
- `python3 build/scripts/build_images.py --version temporal-test --sha 1234567890abcdef --dry-run`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s-full validate local full`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s-temporal2 validate local temporal`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s-infra validate local infra`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s-app-only validate staging app-only`
- `python3 k8s/scripts/manage.py --output /tmp/memoryhive-k8s-temporal-dry validate local temporal --kubectl-dry-run`
- `python3 -c "import yaml, pathlib; [yaml.safe_load(path.read_text()) for path in pathlib.Path('.github/workflows').glob('*.yml')]; print('workflow yaml ok')"`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Next planned slices:
- Completion audit across the full Goal 1 requirements and current worktree.
- EAS initialization and production mobile build artifacts when credentials/project ownership are available.
- Store assets/screenshots and production support/contact metadata.

## 2026-09-06 - Automation Orchestration App Slice

Status: Completed and validated for a root automation app that coordinates seed, smoke, Docker, web Playwright, and mobile Playwright workflows.

Implemented:
- Added `automation/` as a standalone Node orchestration package with `doctor`, `seed`, `validate`, `test`, `test:docker`, `test:docker:cleanup`, and `dry-run` scripts.
- Added `automation/scripts/run.mjs` to run prerequisite checks, optionally start the Docker or Temporal Compose profile, validate readiness, load demo data, run `ops/smoke.sh`, execute frontend live Playwright, execute mobile Expo-web Playwright, and optionally stop or clean the stack.
- Added `automation/README.md` documenting local, Docker-backed, Temporal-backed, cleanup, persona, base URL, and dry-run usage.
- Made frontend live Playwright and mobile Expo-web Playwright accept `MEMORYHIVE_API_URL` so automation can target any backend origin.
- Updated mobile E2E cleanup/setup requests to use the configured API URL instead of hardcoded `127.0.0.1`.
- Added automation validation to CI deployment-assets checks.
- Added `automation/Knowledge.md` generation and updated root Knowledge/README/test report references.
- Fixed frontend Node config type checking by declaring the existing `process.env` usage in `frontend/vite.config.ts`.

Validated:
- `node --check automation/scripts/run.mjs`
- `npm --prefix automation run doctor`
- `npm --prefix automation run dry-run -- --temporal --skip-mobile --cleanup`
- `npx --prefix frontend tsc --noEmit --project frontend/tsconfig.node.json`
- `npm --prefix frontend run test:e2e:live -- --list`
- `npm --prefix frontend run lint`
- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run test:e2e:web -- --list`
- `npm --prefix mobile run lint`
- `npm --prefix mobile run test`
- `python3 -c "import yaml, pathlib; [yaml.safe_load(path.read_text()) for path in pathlib.Path('.github/workflows').glob('*.yml')]; print('workflow yaml ok')"`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Next planned slices:
- Completion audit across the full Goal 1 requirements and current worktree.
- Real Docker-backed automation run when the local stack can be started for a longer integration pass.
- EAS initialization, store assets/screenshots, and production support/contact metadata when external account inputs are available.

## 2026-09-06 - Docker Automation Runtime Validation Slice

Status: Completed and validated for Docker-backed startup, seeding, smoke checks, web E2E, mobile E2E, and cleanup.

Implemented:
- Added a one-shot Docker Compose `migrate` service and made backend, worker, Temporal worker, and Temporal scheduler wait for Alembic migrations before startup.
- Updated `ops/dev-stack.sh migrate` to use the same one-shot migration service that normal stack startup uses.
- Added `ops/dev-stack.sh rate-reset` and wired Docker automation to clear transient Redis `rate:*` counters after readiness so repeated auth-heavy runs avoid stale 429s without deleting volumes.
- Hardened web capture saves when pending tag input commits on blur by submitting on pointer-down, preserving keyboard click activation, and merging pending comma-separated tags into the payload.
- Updated frontend live Playwright for custom confirmation dialogs and current post-delete library behavior.
- Hardened mobile capture and edit saves with the same pending-tag behavior for Expo web while keeping native press semantics unchanged.
- Documented the automation rate-limit reset in `automation/README.md`.

Validated:
- `python3 seed_data.py --base-url http://localhost:8000 --persona engineer`
- `npm --prefix frontend run lint`
- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `npm --prefix frontend run test:e2e:live`
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test`
- `npm --prefix mobile run test:e2e:web`
- `npm --prefix automation run test:docker:cleanup`
- `sh -n ops/dev-stack.sh`
- `node --check automation/scripts/run.mjs`
- `docker compose --env-file .env -f docker-compose.yml config --quiet`
- `docker compose --env-file .env -f docker-compose.yml --profile temporal config --quiet`
- `npm --prefix automation run dry-run`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Next planned slices:
- Completion audit across the full Goal 1 requirements and current worktree.
- EAS initialization and production mobile build artifacts when credentials/project ownership are available.
- Store assets/screenshots and production support/contact metadata when external account inputs are available.

## 2026-09-06 - Completion Audit and Public Support Route Slice

Status: Completed and validated for the local audit artifact and public store-support route. Goal 1 remains active because mobile store submission still needs external account, signing, production deployment, real contact, and asset inputs.

Implemented:
- Added `docs/GOAL-1/COMPLETION_AUDIT.md` with a requirement-area audit of current repo evidence and remaining external gaps.
- Added public web `/support` route for mobile store support URL requirements.
- Linked support from login/register, privacy policy, and account deletion public pages.
- Added public-page unit coverage for support route content and links.
- Updated mobile store readiness, metadata, privacy/data-safety, and README docs to show `/support` exists locally while production deployment and real operator contact remain gaps.

Validated:
- `npm --prefix frontend run lint`
- `npm --prefix frontend test -- PublicPages.test.tsx`
- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Run EAS init and commit the real `extra.eas.projectId`.
- Configure EAS production environment variables, iOS signing credentials, and Android signing credentials.
- Create Apple Developer and Google Play app records.
- Produce and test real iOS `.ipa` and Android `.aab`/`.apk` artifacts.
- Deploy `/privacy`, `/account/delete`, and `/support` on the production domain.
- Replace placeholder support email/contact metadata with the operator's real contact details.
- Create store-ready 1024x1024 icon source, screenshots, Google Play feature graphic, and final Apple/Google store forms.

## 2026-09-06 - Mobile Support URL and Store Readiness Check Slice

Status: Completed and validated for mobile support URL configuration plus a repeatable local store-readiness check. Goal 1 remains active because the checker still reports external release blockers.

Implemented:
- Added `EXPO_PUBLIC_SUPPORT_URL` support in the mobile API configuration, with `/support` derived from the API origin as a local fallback.
- Added a mobile Settings support link next to privacy and account data controls.
- Extended account helper tests for support URL resolution.
- Added `mobile/scripts/check-store-readiness.mjs` and `npm run store:check` to verify local release readiness signals and list remaining blockers.
- Added `mobile/store-assets/` handoff paths for `icon-1024.png`, `feature-graphic.png`, and device screenshots.
- Updated `.env.example`, `.env.production.example`, `README.md`, `mobile/README.md`, iOS/Android build runbooks, mobile store readiness docs, privacy/data-safety docs, and the completion audit.
- Regenerated `mobile/Knowledge.md` after adding the new mobile command.

Validated:
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test -- account-helpers.test.ts`
- `npm --prefix mobile test`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:check` (reports 20 OK, 3 warnings, 6 expected release blockers)
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps from `store:check`:
- EAS project identity.
- Real support contact.
- 1024x1024 store icon source.
- Google Play feature graphic.
- Device screenshots.
- Signed native build artifacts.

## 2026-09-06 - Mobile Store Asset and Screenshot Generation Slice

Status: Completed and validated for deterministic local store artwork, seeded screenshot capture, and store-readiness reporting. Goal 1 remains active because external release identity, production contact, store forms, and signed native artifacts still require account/operator inputs.

Implemented:
- Added `mobile/scripts/generate-store-assets.mjs` and `npm run store:assets` to generate a branded `1024x1024` RGB PNG store icon source, `1024x500` RGB PNG Google Play feature graphic, and asset manifest from source-controlled HTML/CSS.
- Added `mobile/scripts/capture-store-screenshots.mjs` and `npm run store:screenshots` to refresh engineer demo data, authenticate Expo web preview, and capture store-size screenshots for iPhone, iPad, Android phone, and Android tablet.
- Hardened screenshot waits to poll visible Playwright text and require non-empty seeded library content before saving captures.
- Fixed the Expo app tab layout to wait for `AppStateProvider` readiness before rendering direct app routes, preventing local SQLite queries before table initialization.
- Extended `mobile/scripts/check-store-readiness.mjs` to validate RGB PNG dimensions for generated store icon, feature graphic, screenshot files, and release handoff manifest metadata.
- Updated mobile store metadata, readiness, iOS/Android build runbooks, root/mobile README files, and completion audit to reflect generated assets and remaining external blockers.

Validated:
- `npm --prefix mobile run store:assets`
- `npm --prefix mobile run store:screenshots`
- `npm --prefix mobile run store:check` (reports 25 OK, 3 warnings, 3 expected external/release blockers)
- `node --check mobile/scripts/generate-store-assets.mjs`
- `node --check mobile/scripts/capture-store-screenshots.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test`
- `npm --prefix mobile run test:e2e:web`
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`
- Visual QA of `iphone-01-library.png`, `android-phone-02-search.png`, `ipad-03-library.png`, and `android-tablet-04-organize.png`

Generated store assets:
- `mobile/store-assets/icon-1024.png` (`1024x1024`, RGB PNG)
- `mobile/store-assets/feature-graphic.png` (`1024x500`, RGB PNG)
- `mobile/store-assets/screenshots/iphone-01-library.png` (`1290x2796`, RGB PNG)
- `mobile/store-assets/screenshots/android-phone-02-search.png` (`1080x1920`, RGB PNG)
- `mobile/store-assets/screenshots/ipad-03-library.png` (`2048x2732`, RGB PNG)
- `mobile/store-assets/screenshots/android-tablet-04-organize.png` (`1600x2560`, RGB PNG)

Remaining external gaps from `store:check`:
- EAS project identity.
- Real support contact.
- Signed native build artifacts.

## 2026-09-06 - Mobile Store Manifest Metadata Slice

Status: Completed and validated for generated store handoff metadata.

Implemented:
- Added dimensions, purpose, and alt text to `mobile/store-assets/manifest.json`.
- Added platform, form-factor, dimensions, route, screen name, and alt text to `mobile/store-assets/screenshots/manifest.json`.
- Updated `npm run store:check` to fail the local readiness report when generated asset or screenshot metadata is missing.
- Added exact alt-text drafts to `docs/GOAL-1/MOBILE_STORE_METADATA.md` for store-console handoff.

Validated:
- `node --check mobile/scripts/generate-store-assets.mjs`
- `node --check mobile/scripts/capture-store-screenshots.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:assets`
- `sh ops/dev-stack.sh validate`
- `npm --prefix mobile run store:screenshots`
- `npm --prefix mobile run store:check` (reports 25 OK, 3 warnings, 3 expected external/release blockers)

Remaining external gaps:
- EAS project identity.
- Real support contact.
- Signed native build artifacts.

## 2026-09-06 - Agent Knowledge Harness Alignment Slice

Status: Completed and validated for the local KBS requirement.

Implemented:
- Restored the Knowledge-harness entry point in `AGENTS.md` while keeping it titled `Repository Guidelines` and within the contributor-guide word budget.
- Verified `CODEX.md`, `CLAUDE.md`, and `ANTIGRAVITY.md` already direct agents to read `AGENTS.md`, root `Knowledge.md`, and the relevant sub-project `Knowledge.md` before making changes.
- Updated the completion audit to make the `AGENTS.md` contributor-guide plus Knowledge wiring explicit.

Validated:
- `wc -w AGENTS.md` (`400` words)
- `rg -n 'Knowledge.md|generate_knowledge|Before changing code' AGENTS.md CODEX.md CLAUDE.md ANTIGRAVITY.md Knowledge.md`

Remaining external gaps:
- EAS project identity.
- Real support contact.
- Signed native build artifacts.

## 2026-09-06 - Mobile Store Submission Packet Slice

Status: Completed and validated for deterministic App Store / Google Play handoff metadata. Goal 1 remains active because final release identity, production contact metadata, store-console forms, and signed native artifacts still require external account/operator inputs.

Implemented:
- Added `mobile/scripts/generate-store-submission.mjs` and `npm run store:submission` to generate `mobile/store-assets/submission-packet.json` plus `docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md` from `mobile/app.json`, `.env.production.example`, and generated store asset manifests.
- Split Apple and Google short copy into an App Store subtitle (`Capture. Tag. Find.`) and Google Play short description (`Capture links, screenshots, and notes into a searchable offline-first library.`).
- Extended `mobile/scripts/check-store-readiness.mjs` to verify the submission packet structure and enforce App Store subtitle and Google Play short-description character limits.
- Updated README, mobile README, store asset docs, build-test runbooks, metadata notes, privacy/data-safety notes, readiness docs, and completion audit to include the packet workflow.

Validated:
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 29 OK, 3 warnings, 3 expected external/release blockers)
- `node -e "const p=require('./mobile/store-assets/submission-packet.json'); console.log(p.app_store.subtitle.length, p.google_play.short_description.length)"` (`19 78`)
- URL packet check: `api`, `privacy`, `support`, and account deletion URLs resolve from `.env.production.example` or the derived production web origin.

Remaining external gaps:
- EAS project identity.
- Real support contact and production URLs.
- Signed native build artifacts and final store-console forms.

## 2026-09-06 - Public Support Email Configuration Slice

Status: Completed and validated for repository-managed support contact wiring. Goal 1 remains active because the real operator support address, production deployment, EAS project identity, signed artifacts, and store-console forms are external release inputs.

Implemented:
- Added `frontend/src/config.ts` with `VITE_SUPPORT_EMAIL` and a shared `SUPPORT_MAILTO` value for public compliance pages.
- Updated `/support`, `/privacy`, and `/account/delete` pages to render the configured support email instead of hard-coded page-local mailto values.
- Added `VITE_SUPPORT_EMAIL` to development and production env templates, Docker frontend build args, Docker Compose frontend configuration, and CI/release frontend image build args.
- Updated `mobile/scripts/check-store-readiness.mjs` to validate `VITE_SUPPORT_EMAIL` documentation and keep the real-contact blocker tied to production config.
- Updated `mobile/scripts/generate-store-submission.mjs` to include the configured support email in generated store handoff packets.

Validated:
- `npm --prefix frontend run lint`
- `npm --prefix frontend test`
- `npm --prefix frontend run build`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 31 OK, 3 warnings, 3 expected external/release blockers)
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test`
- `docker compose -f docker-compose.yml config --quiet`
- `docker compose --env-file .env.production.example -f docker-compose.prod.yml config --quiet`
- Workflow YAML parse for `.github/workflows/ci.yml` and `.github/workflows/release.yml`
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Replace `VITE_SUPPORT_EMAIL` with the operator's real support address.
- Replace production placeholder URLs and deploy public compliance pages.
- EAS project identity, signed native build artifacts, and final store-console forms.

## 2026-09-06 - Frontend Release Support Email Gate Slice

Status: Completed and validated for production frontend image release gating. Goal 1 remains active because the actual repository variable value, production deployment, EAS project identity, signed native artifacts, and store-console forms remain external release inputs.

Implemented:
- Added a `validate-release-config` job to `.github/workflows/release.yml` that fails before publishing images unless `vars.VITE_SUPPORT_EMAIL` is a non-placeholder email address.
- Changed frontend release image build args to inject `VITE_SUPPORT_EMAIL` from the GitHub repository variable instead of baking `support@memoryhive.example.com` into tagged release images.
- Extended `mobile/scripts/check-store-readiness.mjs` to verify the release workflow uses the repository variable and does not contain the hard-coded placeholder build arg.
- Updated release-readiness docs and the completion audit to track the new release gate.

Validated:
- Workflow YAML parse for `.github/workflows/ci.yml` and `.github/workflows/release.yml`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:check` (reports 32 OK, 3 warnings, 3 expected external/release blockers)

Remaining external gaps:
- Set GitHub repository variable `VITE_SUPPORT_EMAIL` to the operator's real support address.
- Replace production placeholder URLs and deploy public compliance pages.
- EAS project identity, signed native build artifacts, and final store-console forms.

## 2026-09-06 - Mobile Category Management Parity Slice

Status: Completed and validated for repository-local mobile organization parity. Goal 1 remains active because release identity, production contact/URL values, signed native artifacts, and store-console forms remain external inputs.

Implemented:
- Added mobile `Category` and `ManagedTag` contracts plus `categoriesApi` and `tagsApi` wrappers for the existing `/categories` and `/tags` backend endpoints.
- Extended `AppStateProvider` to refresh categories/tags after sync, expose category create/delete and tag delete actions, and clear organization state on logout/account removal.
- Added local cache helpers that remove deleted category/tag references from cached items and scrub queued item mutation payloads after the server accepts the organization delete.
- Added `CategoryPicker` and wired category assignment into mobile capture and item edit flows.
- Added category route params, filter pills, and category rails to mobile Library and Search.
- Rebuilt mobile Organize with status/type navigation, category create/delete/filter rows, tag delete/filter rows, and server-backed organization refresh.
- Refreshed store screenshots, screenshot metadata, and the generated store submission packet after the Organize UI changed.

Validated:
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test` (17 tests)
- `npm --prefix mobile run test:e2e:web`
- `sh ops/dev-stack.sh validate`
- `npm --prefix mobile run store:screenshots`
- Visual QA of `mobile/store-assets/screenshots/iphone-01-library.png`, `android-phone-02-search.png`, and `android-tablet-04-organize.png`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 32 OK, 3 warnings, 3 expected external/release blockers)

Remaining external gaps:
- Set real production support email/URLs and deploy compliance pages.
- EAS project identity.
- Signed native build artifacts and final store-console forms.

## 2026-09-06 - Mobile Native Build Evidence Readiness Slice

Status: Completed and validated for repository-local native build evidence tracking. Goal 1 remains active because actual signed artifacts, device testing, production release identity, production URLs/contact, reviewer account, and store-console forms are external inputs.

Implemented:
- Added `mobile/builds/native-artifacts.example.json` and `mobile/builds/README.md` to define the expected release evidence for iOS and Android production builds.
- Updated `.gitignore` so signed `.ipa`, `.aab`, and `.apk` files under `mobile/builds/` stay out of git while the non-secret native build evidence manifest can be committed or shared.
- Extended `mobile/scripts/check-store-readiness.mjs` to check iOS and Android artifacts separately, require non-empty artifact files, reject placeholder EAS build IDs, require iOS device-test evidence, and require Android `targetSdkVersion >= 36` plus final `RECORD_AUDIO` absence evidence.
- Updated mobile release docs, root/mobile README, store-assets README, generated submission packet blockers, completion audit, and generated mobile Knowledge docs to reference the native build evidence workflow.

Validated:
- Official Google Play target API requirement rechecked: new apps and updates must target Android 16 / API 36 or higher from August 31, 2026.
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 35 OK, 3 warnings, 7 expected external/release blockers)
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Set real production support email/URLs and deploy compliance pages.
- Create the dedicated store-review account and replace `STORE_REVIEW_ACCOUNT_EMAIL`.
- EAS project identity and signing credentials.
- Signed iOS/Android build artifacts, native device-test evidence, Android target/permission evidence, and final store-console forms.

## 2026-09-06 - Mobile Store Review Access Readiness Slice

Status: Completed and validated for reviewer-account handoff tracking. Goal 1 remains active because the actual reviewer account, production URLs/contact, EAS identity, signed artifacts, and store-console forms are external release inputs.

Implemented:
- Added `STORE_REVIEW_ACCOUNT_EMAIL` to development and production env templates as the source-controlled placeholder for a dedicated App Store / Google Play review account.
- Updated `mobile/scripts/generate-store-submission.mjs` so the generated JSON and Markdown handoff include review-access sections for both App Store Connect and Play Console while keeping passwords out of committed artifacts.
- Extended `mobile/scripts/check-store-readiness.mjs` to validate the review-account handoff fields and report a blocker while the reviewer email still uses an example-domain placeholder.
- Updated root/mobile README and mobile store readiness, metadata, privacy/data-safety, iOS, and Android release docs with review-account setup guidance.

Validated:
- `node --check mobile/scripts/generate-store-submission.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 34 OK, 3 warnings, 4 expected external/release blockers)

Remaining external gaps:
- Set real production support email/URLs and deploy compliance pages.
- Create the dedicated store-review account and replace `STORE_REVIEW_ACCOUNT_EMAIL`.
- EAS project identity.
- Signed native build artifacts and final store-console forms.

## 2026-09-06 - Mobile Category E2E Hardening Slice

Status: Completed and validated for the mobile Expo-web Playwright workflow. Goal 1 remains active because the remaining blockers are external release inputs.

Implemented:
- Extended `mobile/e2e/mobile-workflow.e2e.ts` to create a category from the mobile Organize tab during the disposable-user workflow.
- Updated the capture flow assertions to assign a note to that category through `CategoryPicker`.
- Added a negative control item with `None` selected, then verified the Library category filter keeps the categorized note visible and hides the uncategorized note.
- Preserved the existing registration, search, reload persistence, account cleanup, and seeded-login coverage.

Validated:
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test` (17 tests)
- `sh ops/dev-stack.sh validate`
- `npm --prefix mobile run test:e2e:web`
- `npm --prefix mobile run store:check` (reports 32 OK, 3 warnings, 3 expected external/release blockers)
- `git diff --check`

Remaining external gaps:
- Set real production support email/URLs and deploy compliance pages.
- EAS project identity.
- Signed native build artifacts and final store-console forms.

## 2026-09-06 - Mobile Production Config Readiness Slice

Status: Completed and validated for production mobile store configuration gating. Goal 1 remains active because the real production URLs/contact, reviewer account, EAS identity, signed artifacts, native test evidence, and store-console forms are external release inputs.

Implemented:
- Updated `mobile/scripts/check-store-readiness.mjs` so `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRIVACY_POLICY_URL`, and `EXPO_PUBLIC_SUPPORT_URL` must resolve to non-placeholder HTTPS values before release.
- Changed production URL placeholder findings from warnings to blockers while keeping the production env template documentation checks.
- Made `VITE_SUPPORT_EMAIL` and `STORE_REVIEW_ACCOUNT_EMAIL` checks honor release environment overrides and report deterministic OK/BLOCKED results.
- Updated `mobile/scripts/generate-store-submission.mjs` so generated JSON/Markdown handoff packets use the same release environment overrides for production URLs, support email, and reviewer email.
- Updated root/mobile/store-assets README files, mobile store readiness docs, generated submission packet, and completion audit for the new blocker classification.

Validated:
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 35 OK, 0 warnings, 10 expected external/release blockers)
- Release override smoke: `store:check` reports 40 OK, 0 warnings, 5 blockers when non-placeholder URL/contact/reviewer env vars are supplied.

Remaining external gaps:
- Provide real production URL, support email, and reviewer account values through the release environment.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Release URL and Email Quality Gate Slice

Status: Completed and validated for stricter mobile release config quality checks. Goal 1 remains active because real production deployment, support/reviewer accounts, EAS identity, signed artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Hardened `mobile/scripts/check-store-readiness.mjs` so production URLs must be public HTTPS values, not localhost, private IPs, `.local`, `.test`, `.invalid`, or example domains.
- Required `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRIVACY_POLICY_URL`, and `EXPO_PUBLIC_SUPPORT_URL` to match the deployed route contract: `/api/v1`, `/privacy`, and `/support`.
- Added syntactic email validation for `VITE_SUPPORT_EMAIL` and `STORE_REVIEW_ACCOUNT_EMAIL`, while keeping placeholder/reserved domains blocked.
- Updated root/mobile/store-assets README files, mobile iOS/Android build runbooks, mobile store readiness, metadata, privacy/data-safety, and completion audit docs with the stricter release config contract.

Validated:
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 36 OK, 0 warnings, 10 expected external/release blockers)
- Negative release config smoke: localhost/private/reserved/documentation URLs, wrong route path, malformed support email, and `.local` reviewer email are blocked.
- Matched release config smoke: `store:submission` plus `store:check` under public HTTPS route values and valid emails reports 41 OK, 0 warnings, 5 blockers.

Remaining external gaps:
- Provide real public production URL, support email, and reviewer account values through the release environment.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Native Evidence Schema Hardening Slice

Status: Completed and validated for stricter native build evidence validation. Goal 1 remains active because real signed artifacts, EAS identity, production config, reviewer account, native testing, and store-console forms are external release inputs.

Implemented:
- Tightened `mobile/scripts/check-store-readiness.mjs` so recorded iOS artifacts must be non-empty `.ipa` files under `mobile/builds/`.
- Tightened recorded Android artifacts to non-empty `.aab` or `.apk` files under `mobile/builds/`.
- Changed iOS and Android test evidence checks to require at least two distinct tested device records per platform.
- Updated `mobile/builds/README.md`, mobile README, iOS/Android build runbooks, mobile store readiness docs, and completion audit to match the stricter evidence schema.

Validated:
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 36 OK, 0 warnings, 10 expected external/release blockers)
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Provide real production URL, support email, and reviewer account values through the release environment.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Submission Packet Consistency Slice

Status: Completed and validated for release packet/config consistency. Goal 1 remains active because the real production URLs/contact, reviewer account, EAS identity, signed artifacts, native test evidence, and store-console forms are external release inputs.

Implemented:
- Extended `mobile/scripts/check-store-readiness.mjs` to derive the expected production URLs, support email, and reviewer email from the same release environment path used by `store:submission`.
- Added a `Store submission packet release config` check that blocks when `mobile/store-assets/submission-packet.json` does not match the configured release values.
- Updated root/mobile/store-assets README files, mobile store readiness docs, and the completion audit to instruct operators to run `store:submission` and `store:check` with the same release environment.

Validated:
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 36 OK, 0 warnings, 10 expected external/release blockers)
- Stale-packet override smoke: `store:check` reports 40 OK, 0 warnings, 6 blockers when release env overrides are supplied without regenerating the packet.
- Matched override smoke: `store:submission` plus `store:check` under the same non-placeholder release env reports 41 OK, 0 warnings, 5 blockers.

Remaining external gaps:
- Provide real production URL, support email, and reviewer account values through the release environment.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Store Env File Handoff Slice

Status: Completed and validated for access-controlled release env-file loading. Goal 1 remains active because real production deployment, support/reviewer accounts, EAS identity, signed artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Added `mobile/scripts/store-env.mjs` as a shared parser for `--release-env-file`, supporting comments, `export KEY=value`, and quoted values.
- Updated `mobile/scripts/generate-store-submission.mjs` and `mobile/scripts/check-store-readiness.mjs` to resolve release config in this order: shell environment, `--release-env-file`, `.env.production.example`, then script fallback.
- Added readiness output for a loaded release env file without printing secret-like values from the file.
- Updated root/mobile/store-assets README files, iOS/Android build runbooks, mobile store readiness docs, and completion audit with exact `--release-env-file` release handoff commands.

Validated:
- `node --check mobile/scripts/store-env.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 36 OK, 0 warnings, 10 expected external/release blockers)
- Env-file smoke: `store:submission -- --release-env-file /tmp/...` plus `store:check -- --release-env-file /tmp/...` reports 42 OK, 0 warnings, 5 blockers, with only EAS/native evidence blockers remaining.

Remaining external gaps:
- Provide a real access-controlled release env file with public production URLs, support email, and reviewer account values.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Store Env Parser Coverage Slice

Status: Completed and validated for release env parser coverage and flag clarity. Goal 1 remains active because real production deployment, support/reviewer accounts, EAS identity, signed artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Removed the undocumented `--env-file` alias from `mobile/scripts/store-env.mjs` so store scripts expose only the collision-free `--release-env-file` flag.
- Added a native `process.execArgv` guard so accidental Node `--env-file` use fails before store config is read.
- Added `mobile/tests/store-env.test.mjs` covering comments, `export KEY=value`, quoted values, inline comments, invalid-line errors, supported flag forms, missing flag values, file loading, and blank-value lookup behavior.
- Updated the completion audit to cite the parser test as evidence for the release env-file workflow.

Validated:
- `node --check mobile/scripts/store-env.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `npm --prefix mobile test -- store-env` (6 tests)
- Missing release env file check fails with `Env file not found`.
- Direct and npm-script `--env-file` invocations fail with `Use --release-env-file for store scripts; --env-file is reserved by Node.`
- `npm --prefix mobile run store:submission -- --release-env-file /tmp/...`
- `npm --prefix mobile run store:check -- --release-env-file /tmp/...` (reports 42 OK, 0 warnings, 5 blockers)
- `npm --prefix mobile run store:check` (reports 36 OK, 0 warnings, 10 expected external/release blockers)

Remaining external gaps:
- Provide a real access-controlled release env file with public production URLs, support email, and reviewer account values.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Store Release Config Resolver Slice

Status: Completed and validated for shared store release config resolution. Goal 1 remains active because real production deployment, support/reviewer accounts, EAS identity, signed artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Added `mobile/scripts/store-release-config.mjs` to resolve release values in one place using shell environment, `--release-env-file`, `.env.production.example`, and script fallback precedence.
- Moved production URL specs, public HTTPS route validation, placeholder/reserved-domain checks, and support/reviewer email validation into the shared resolver module.
- Updated `mobile/scripts/generate-store-submission.mjs` and `mobile/scripts/check-store-readiness.mjs` to consume the same resolved URLs, contacts, reviewer account email, and validation helpers.
- Added `mobile/tests/store-release-config.test.mjs` coverage for template fallback, env-file override, shell override, derived support/privacy/deletion URLs, production URL validation, and production email validation.
- Updated the completion audit and decision log to document the shared resolver contract.

Validated:
- `node --check mobile/scripts/store-env.mjs`
- `node --check mobile/scripts/store-release-config.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `npm --prefix mobile test -- store-release-config` (6 tests)
- `npm --prefix mobile test` (7 files, 29 tests)
- `npm --prefix mobile run lint`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 36 OK, 0 warnings, 10 expected external/release blockers)
- Release env-file smoke: `store:submission` plus `store:check` with public HTTPS route values and valid emails reports 42 OK, 0 warnings, 5 blockers.
- Restored the default generated submission packet after the env-file smoke and verified no smoke values remained in `mobile/store-assets` or `docs/GOAL-1`.

Remaining external gaps:
- Provide a real access-controlled release env file with public production URLs, support email, and reviewer account values.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, and complete final store-console forms.

## 2026-09-06 - Mobile Store Privacy Disclosure Config Slice

Status: Completed and validated for explicit App Privacy / Data safety release disclosure handoff. Goal 1 remains active because real production deployment, support/reviewer accounts, EAS identity, signed artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Added non-secret `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` release handoff variables to `.env.example` and `.env.production.example`.
- Extended `mobile/scripts/store-release-config.mjs` to resolve disclosure values, validate allowed modes, expose sanitized privacy disclosure objects, and detect backend enrichment endpoints paired with an incorrect `none` AI disclosure.
- Updated `mobile/scripts/generate-store-submission.mjs` so generated JSON and Markdown store packets include external AI processing and production telemetry declarations without printing webhook or model endpoint values.
- Updated `mobile/scripts/check-store-readiness.mjs` to verify disclosure documentation, allowed values, AI enrichment consistency, and submission-packet consistency.
- Updated mobile readiness, metadata, privacy/data-safety, iOS/Android build runbooks, root README, mobile README, store-assets README, completion audit, and decision log for the new disclosure contract.

Validated:
- `node --check mobile/scripts/store-env.mjs`
- `node --check mobile/scripts/store-release-config.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `npm --prefix mobile test -- store-release-config` (8 tests)
- `npm --prefix mobile test` (7 files, 31 tests)
- `npm --prefix mobile run lint`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 43 OK, 0 warnings, 10 expected external/release blockers)
- Valid release env-file smoke with public URLs, valid emails, `STORE_EXTERNAL_AI_PROCESSING=third_party`, and `STORE_PRODUCTION_TELEMETRY=crash_reporting` reports 49 OK, 0 warnings, 5 blockers.
- Enrichment mismatch smoke with `N8N_WEBHOOK_URL` plus `STORE_EXTERNAL_AI_PROCESSING=none` reports 48 OK, 0 warnings, 6 blockers, including the expected AI disclosure consistency blocker.
- Restored the default generated submission packet after release-env smokes and verified no smoke values remained in generated handoff artifacts.
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Provide a real access-controlled release env file with public production URLs, support email, reviewer account value, and privacy disclosure values that match production services.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, verify final privacy form answers, and complete store-console forms.

## 2026-09-06 - Mobile Native Build Evidence Validator Slice

Status: Completed and validated for unit-tested native build evidence interpretation. Goal 1 remains active because actual signed native artifacts, EAS identity, production deployment, reviewer account, native testing, and store-console forms are external release inputs.

Implemented:
- Added `mobile/scripts/native-build-evidence.mjs` with the shared native evidence rules used by `store:check`.
- Extracted artifact path normalization, required platform extensions, non-empty artifact checks, placeholder build-ID rejection, distinct tested-device counting, iOS production evidence validation, and Android target/permission validation out of the CLI script.
- Updated `mobile/scripts/check-store-readiness.mjs` to consume the shared validator while preserving the same readiness output and blocker classifications.
- Added `mobile/tests/native-build-evidence.test.mjs` coverage for in-repo vs out-of-repo artifact paths, wrong extensions, missing files, duplicate devices, placeholder EAS build IDs, non-production profiles, Android target SDK minimum, and final `RECORD_AUDIO` evidence.
- Updated the completion audit and decision log to document the tested native evidence contract.

Validated:
- `node --check mobile/scripts/native-build-evidence.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile test -- native-build-evidence` (5 tests)
- `npm --prefix mobile test` (8 files, 36 tests)
- `npm --prefix mobile run lint`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 43 OK, 0 warnings, 10 expected external/release blockers)
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, verify final privacy form answers, and complete store-console forms.

## 2026-09-06 - Mobile Submission Packet Validator Slice

Status: Completed and validated for unit-tested store submission packet validation. Goal 1 remains active because actual production release config, reviewer account setup, EAS identity, signed native artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Added `mobile/scripts/store-submission-packet.mjs` with shared packet validation helpers used by `store:check`.
- Extracted packet required-field validation, release-config consistency checks, App Store subtitle and Google Play short-description limits, and reviewer password safety into the shared module.
- Added a `Store review password handling` readiness check so generated packets fail if reviewer passwords are committed instead of out-of-band store-console instructions.
- Added `mobile/tests/store-submission-packet.test.mjs` coverage for valid packets, missing sections, stale release URLs/disclosures, committed reviewer passwords, and copy-length violations.
- Updated mobile store readiness and completion audit docs, and recorded the decision in `DECISIONS-GOAL-1.MD`.

Validated:
- `node --check mobile/scripts/store-submission-packet.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile test -- store-submission-packet` (5 tests)
- `npm --prefix mobile test` (9 files, 41 tests)
- `npm --prefix mobile run lint`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 44 OK, 0 warnings, 10 expected external/release blockers)
- `python3 scripts/generate_knowledge.py`
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Provide real production release config and reviewer account metadata.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, verify final privacy form answers, and complete store-console forms.

## 2026-09-06 - Mobile EAS Release Evidence Validator Slice

Status: Completed and validated for unit-tested EAS release setup evidence gates. Goal 1 remains active because actual EAS project ownership, production environment configuration, signing credentials, submit credentials, signed artifacts, native testing, production URLs/contact, reviewer account setup, and store-console completion are external release inputs.

Implemented:
- Added `mobile/scripts/eas-release-readiness.mjs` with shared checks for EAS project identity, CLI config, development/preview/production build profile shape, production submit profile, production environment evidence, iOS signing evidence, and Android signing evidence.
- Added `mobile/builds/eas-release-evidence.example.json` as the non-secret handoff template for EAS project ID, production environment variables, iOS signing, Android keystore/Play app signing, service account, and submit setup.
- Updated `.gitignore` so the EAS evidence template and completed non-secret evidence manifest can be tracked while signed native artifacts remain ignored.
- Updated `mobile/scripts/check-store-readiness.mjs` so strict readiness cannot pass without completed EAS release evidence.
- Updated mobile build README, iOS/Android runbooks, mobile readiness docs, root/mobile README release guidance, generated store submission blocker list, completion audit, and decision log.

Validated:
- `node --check mobile/scripts/eas-release-readiness.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile test -- eas-release-readiness` (4 tests)
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 47 OK, 0 warnings, 16 expected external/release blockers)

Remaining external gaps:
- Run EAS init and commit the real `extra.eas.projectId`.
- Configure EAS production environment, iOS signing, Android signing, and submit credentials, then create `mobile/builds/eas-release-evidence.json`.
- Provide real production release config and reviewer account metadata.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence.
- Complete App Store Connect and Play Console forms, verify final privacy disclosures, and create `mobile/store-assets/store-console-evidence.json`.

## 2026-09-06 - Mobile Store Console Evidence Validator Slice

Status: Completed and validated for unit-tested store-console and final privacy evidence gates. Goal 1 remains active because actual production release config, reviewer account setup, EAS identity, signed native artifacts, native testing, store-console completion, and legal/product privacy verification are external release inputs.

Implemented:
- Added `mobile/store-assets/store-console-evidence.example.json` as the handoff template for final App Store Connect, Play Console, and privacy verification evidence.
- Added `mobile/scripts/store-console-evidence.mjs` with shared checks for App Store app record/listing/screenshot/privacy/age-rating/export-compliance/review-info evidence.
- Added Google Play evidence checks for app record/listing, feature graphic, screenshots, Data safety, content rating, target audience, app access, support email, deletion URL, and review account alignment.
- Added final privacy verification checks that require owner verification, matching `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` values, retention review, and deletion-flow verification.
- Updated `mobile/scripts/check-store-readiness.mjs` so strict readiness cannot pass without the completed evidence file.
- Updated README, mobile README, store-assets README, mobile readiness/privacy docs, completion audit, submission packet generation, and decision log.

Validated:
- `node --check mobile/scripts/store-console-evidence.mjs`
- `node --check mobile/scripts/generate-store-submission.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile test -- store-console-evidence` (4 tests)
- `npm --prefix mobile test` (11 files, 50 tests)
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 45 OK, 0 warnings, 13 expected external/release blockers)

Remaining external gaps:
- Provide real production release config and reviewer account metadata.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence.
- Complete App Store Connect and Play Console forms, verify final privacy disclosures, and create `mobile/store-assets/store-console-evidence.json`.

## 2026-09-06 - Mobile Store Asset Readiness Validator Slice

Status: Completed and validated for unit-tested store asset and screenshot readiness rules. Goal 1 remains active because actual production release config, reviewer account setup, EAS identity, signed native artifacts, native testing, and store-console forms are external release inputs.

Implemented:
- Added `mobile/scripts/store-asset-readiness.mjs` with shared PNG metadata parsing, RGB PNG checks, store icon/feature graphic readiness checks, expected screenshot specs, and asset/screenshot manifest validation.
- Updated `mobile/scripts/check-store-readiness.mjs` to use the shared asset validator while preserving the readiness report and default blocker count.
- Made existing expected screenshot files invalid when they are malformed, wrong-size, or non-RGB instead of only checking dimensions after successful PNG parsing.
- Added `mobile/tests/store-asset-readiness.test.mjs` coverage for PNG parsing, store image dimensions, manifest metadata, missing screenshots, malformed screenshots, wrong-size screenshots, and non-RGB screenshots.
- Updated mobile store readiness, metadata, store-assets handoff docs, completion audit, and decision log for the tested asset-readiness contract.

Validated:
- `node --check mobile/scripts/store-asset-readiness.mjs`
- `node --check mobile/scripts/check-store-readiness.mjs`
- `npm --prefix mobile test -- store-asset-readiness` (5 tests)
- `npm --prefix mobile test` (10 files, 46 tests)
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile run store:submission`
- `npm --prefix mobile run store:check` (reports 44 OK, 0 warnings, 10 expected external/release blockers)

Remaining external gaps:
- Provide real production release config and reviewer account metadata.
- Run EAS init and configure production signing/environment.
- Produce signed iOS/Android artifacts under `mobile/builds/`, record native device-test and Android target/permission evidence, verify final privacy form answers, and complete store-console forms.

## 2026-09-06 - Mobile Release Readiness CI Gate Slice

Status: Completed and validated for repository-owned mobile release readiness. Goal 1 remains active because the final store release still requires external accounts, production deployment, signing, native artifacts/tests, and store-console evidence.

Implemented:
- Added `mobile/scripts/store-readiness-results.mjs` to classify and summarize repository versus external release blockers.
- Added `store:check:ci`, which fails on repository defects while preserving external blockers as visible release prerequisites; retained `--strict` as the all-blocker final release gate.
- Added focused tests for readiness summaries and default, CI, and strict exit behavior.
- Updated mobile CI to check the committed store submission packet and run the repository readiness gate.
- Updated contributor and release documentation with the two-gate workflow.

Validated:
- `node --check mobile/scripts/check-store-readiness.mjs`
- `node --check mobile/scripts/store-readiness-results.mjs`
- `npm --prefix mobile test -- store-readiness-results` (4 tests)
- `npm --prefix mobile run store:submission` (deterministic output; hashes unchanged)
- `npm --prefix mobile run store:check:ci` (47 OK, 0 repository blockers, 16 release blockers; exit 0)
- Invalid-disclosure smoke with `STORE_EXTERNAL_AI_PROCESSING=invalid` (2 repository blockers, 16 release blockers; exit 1)
- `npm --prefix mobile run store:check -- --strict` (47 OK, 0 repository blockers, 16 release blockers; expected exit 1)

Remaining external gaps:
- Run EAS init and configure production environment, signing, and submit credentials.
- Provide public production URLs, operator support contact, and a dedicated reviewer account.
- Produce signed iOS/Android artifacts, record native test evidence, complete store forms, and create the final EAS/native/store-console evidence files.

## 2026-09-06 - Docker Runtime Revalidation And Mobile Web Shadow Cleanup Slice

Status: Completed and validated for current Docker-backed API, web, and mobile-web behavior. Goal 1 remains active only for external mobile release prerequisites.

Implemented:
- Re-ran the complete automation lifecycle from stopped services through Compose rebuild, migrations, readiness checks, idempotent persona seeding, authenticated API smoke, web Playwright, mobile Expo-web Playwright, and non-destructive cleanup.
- Replaced legacy React Native Web `shadow*` rendering with platform-selected `boxShadow` values while preserving native iOS/Android shadows and elevation.
- Updated the application test report and completion audit with fresh runtime evidence and current unit-test counts.

Validated:
- `npm --prefix automation run test:docker:cleanup` (full stack, API smoke, web E2E, mobile-web E2E, cleanup; exit 0)
- Seed validation: four personas, 53 existing demo items, no duplicates created.
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test` (13 files, 58 tests)
- `npm --prefix automation run test:docker:cleanup -- --skip-web` (mobile regression rerun; exit 0, no legacy shadow warnings)
- Post-run `docker compose ps --all` reports no running containers.

Remaining external gaps:
- Run EAS init and configure production environment, signing, and submit credentials.
- Provide public production URLs, operator support contact, and a dedicated reviewer account.
- Produce signed iOS/Android artifacts, record physical-device evidence, complete store forms, and create final evidence manifests.

## 2026-09-06 - Read-Only Store Submission Drift Gate Slice

Status: Completed and validated for deterministic generated-output enforcement. Goal 1 remains active because EAS authentication and final release inputs are external.

Implemented:
- Added `store:submission:check` to derive the expected JSON and Markdown packets and compare their bytes without modifying either file.
- Added a pure generated-output mismatch helper with tests for current, stale, and missing files.
- Made the generator reject unknown command-line options instead of silently ignoring them.
- Replaced CI's generate-then-`git diff` sequence with the read-only check, which also catches outputs deleted from source control.
- Verified the EAS CLI state directly; this machine is not logged in and cannot initialize or inspect an EAS project without `eas login` or `EXPO_TOKEN`.

Validated:
- `node --check mobile/scripts/generate-store-submission.mjs`
- `node --check mobile/scripts/generated-output.mjs`
- `npm --prefix mobile test -- generated-output` (2 tests)
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test` (14 files, 60 tests)
- `npm --prefix mobile run store:submission:check` (current; exit 0)
- Before/after generated-packet hashes are identical after the read-only check.
- Release-config mismatch smoke (reports stale JSON; exit 1 without file changes)
- Unknown-option smoke (reports `Unknown option`; exit 1)
- `npx --yes eas-cli@latest whoami` (reports `Not logged in`)
- `npx --yes eas-cli@latest project:info --json --non-interactive` (requires Expo authentication)

Remaining external gaps:
- Provide an authenticated Expo account or scoped `EXPO_TOKEN`, initialize the EAS project, and configure production environment/signing/submit credentials.
- Provide production URLs and contacts, signed native artifacts and physical-device evidence, and completed store-console/privacy evidence.

## 2026-09-06 - Guarded Mobile EAS Build Workflow Slice

Status: Completed and validated for repository-side native build automation. Goal 1 remains active because EAS account initialization, credentials, actual builds, native tests, and store submission are external.

Implemented:
- Added explicit `development`, `preview`, and `production` EAS environment selection to the matching build profiles.
- Added a tested EAS CI preflight for `EXPO_TOKEN`, committed project ID, CLI configuration, and build-profile shape.
- Added the manually dispatched `Mobile EAS Build` workflow with bounded `ios`, `android`, and `all` choices.
- Made the workflow run packet/readiness gates, freeze existing credentials, queue non-interactively without waiting, avoid auto-submission, and upload the JSON build request for 30 days.
- Updated mobile build/readiness runbooks and evidence handoff documentation.

Validated:
- `node --check mobile/scripts/check-eas-ci-preflight.mjs`
- `node --check mobile/scripts/eas-release-readiness.mjs`
- `npm --prefix mobile test -- eas-release-readiness` (5 tests)
- `npm --prefix mobile run typecheck`
- `npm --prefix mobile run lint`
- `npm --prefix mobile test` (14 files, 61 tests)
- Actual `mobile/eas.json` CLI and build-profile validation passes.
- Local preflight reports exactly the missing `EXPO_TOKEN` and EAS project ID.
- Preflight with a test token reports only the missing EAS project ID.
- `npm --prefix mobile run store:check:ci` (47 OK, 0 repository blockers, 16 release blockers)
- Ruby YAML parse of `.github/workflows/mobile-eas-build.yml`
- EAS CLI help confirms `--platform`, `--profile`, `--non-interactive`, `--no-wait`, `--freeze-credentials`, `--json`, and `--message` support.
- All `.github/workflows/*.yml` files parse as YAML.

Remaining external gaps:
- Authenticate Expo/EAS, initialize the project, configure production environment and existing signing credentials, and add the scoped `EXPO_TOKEN` repository secret.
- Dispatch and monitor the native builds, download artifacts, execute physical-device tests, and complete evidence manifests plus store-console forms.

## 2026-09-06 - Destructive Action Confirmation Coverage Slice

Status: Completed and validated for the requested web and mobile confirmation behavior. Goal 1 remains active only for external mobile release prerequisites.

Implemented:
- Inventoried every web/mobile item, organization, account, admin-user, backup, processing-retry, and sign-out destructive or consequential action against its confirmation boundary.
- Confirmed that web account deletion already uses an accessible modal requiring the current password and exact typed `DELETE`; retained this stronger single boundary instead of nesting another dialog.
- Added card archive tests covering cancel/state preservation and confirmed visible archive state changes.
- Added component tests for detail-page item deletion, category deletion with item detachment, tag-delete cancellation, and password plus typed account-deletion gating.
- Updated the completion audit with explicit destructive-action traceability.

Validated:
- `npm --prefix frontend test -- LibraryPage DestructiveActions` (2 files, 10 tests)
- `npm --prefix frontend run lint`
- `npm --prefix frontend test` (5 files, 17 tests)
- `npm --prefix frontend run build`

Remaining external gaps:
- Authenticate and initialize EAS, configure production release identity/environment/signing, and queue native builds.
- Complete physical-device verification, signed artifact evidence, production URLs/contact setup, and App Store/Play Console forms.

## 2026-09-06 - Goal Status Handoff Package

Status: Completed and validated for documentation handoff. Goal 1 remains
externally blocked and is not ready to mark complete.

Implemented:
- Added `docs/GOAL-1/Goal Status/README.md` as the canonical restart point.
- Added a concise Goal 1 summary covering requested scope, delivered outcomes,
  the current verdict, and pickup commands.
- Added a numbered matrix mapping every original requirement to status and
  authoritative evidence, with signed native outcomes labeled external.
- Added a general status report with requirement-area traceability, current
  validation results, all 16 external blockers, owners, and completion order.
- Linked the handoff package from the completion audit and generated Knowledge
  harness.

Validated:
- All status links resolve to files in the current tree.
- The blocker register matches `store:check:ci`: 47 OK, 0 repository blockers,
  and 16 external release blockers.
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- Supply the production release inputs and credentials listed in the general
  status report.
- Produce signed builds, complete native-device testing and store-console forms,
  then pass `store:check -- --strict` with zero blockers.

## 2026-09-06 - Goal Status Validation Results Addendum

Status: Completed and validated for restart evidence. Goal 1 remains externally
blocked.

Implemented:
- Added `docs/GOAL-1/Goal Status/VALIDATION-RESULTS.md` with exact repository
  gate commands, pass counts, runtime evidence, dependency warnings, and the
  external checks that remain unproven.
- Linked the validation record from the status index and general report.

Validated:
- All five status-package Markdown files exist and their local links resolve.
- The validation record matches current backend, frontend, mobile, deployment,
  Knowledge, and store-readiness command results.
- `python3 scripts/generate_knowledge.py --check`
- `git diff --check`

Remaining external gaps:
- The 16 release blockers in the general status report still require operator,
  Expo/EAS, Apple/Google store, release-engineering, and mobile-QA action.
