# Decisions - Goal 1

## 2026-09-06

### D-001 - Prioritize the Web Library and Card-Actions Slice First

Decision: Implement the web library filter, pill, tag, and confirmation flows before admin, mobile, Temporal, and Kubernetes work.

Rationale: The backend already exposes item filtering by type/category/tag/favorite/archive, item tag updates, and favorite/archive endpoints. This made the web slice the fastest high-value feature set to complete with low backend risk.

### D-002 - Store Library Filters in URL Query Parameters

Decision: Use query parameters for `q`, `type`, `category`, `tag`, and `summary` instead of local-only component state.

Rationale: Organize and detail views can deep-link users back to Library with filters applied, and filter state remains shareable and reload-safe.

### D-003 - Use Shared React Confirmation UI

Decision: Add a reusable `ConfirmDialog` and use it for item favorite/archive/delete and organization deletes touched in this slice.

Rationale: Native `window.confirm` is inconsistent with the app UI and cannot support the same accessible, styled confirmation pattern across web workflows.

### D-004 - Reuse the Existing Item Tag Update Contract

Decision: Implement tag and untag from item edit by sending the full normalized tag list through `PATCH /items/{id}`.

Rationale: The API already owns tag normalization and item-tag replacement, so no new backend endpoint is needed for the current item-level tag management workflow.

### D-005 - Keep Summary Count Filters as Library-Scoped Controls

Decision: Summary count filters are rendered only on the main Library route. Favorites and Archive routes keep their route-specific semantics.

Rationale: This avoids hidden filter combinations on specialized routes while still making the requested top library numbers interactive.

### D-006 - Bootstrap Admins Explicitly in Production

Decision: Add `users.role` with `admin` and `user` values. In development, the first registered account becomes admin. In production, admins should be bootstrapped with `ADMIN_BOOTSTRAP_EMAILS`.

Rationale: The app needs an initial admin path without allowing arbitrary role selection during registration.

### D-007 - Keep Admin User Management Under `/api/v1/admin`

Decision: Add admin dashboard and user-management routes under a dedicated admin router.

Rationale: A distinct router keeps privileged workflows isolated from user-owned item/account APIs and makes authorization checks auditable.

### D-008 - Share Account Deletion Lifecycle Logic

Decision: Move account deletion cleanup into `app/services/account_lifecycle.py` and reuse it for user self-delete and admin user delete.

Rationale: Admin deletion must remove user-owned data and stored assets through the same audited cleanup path as account deletion.

### D-009 - Protect Admins From Self-Lockout

Decision: Admin APIs reject self-disable, self-demotion, and self-delete.

Rationale: This prevents a single admin action from removing the only privileged route back into the system.

### D-010 - Isolate Rate-Limit Identity in API Tests

Decision: Give each `api_client` fixture a unique ASGI client host.

Rationale: Local rate-limit buckets are process-local and were leaking between integration tests that register users through the same auth endpoints.

### D-011 - Use Session Versioning for Password-Change Invalidation

Decision: Add `users.session_version` and include it in new access tokens. Password changes increment the version and revoke all refresh tokens.

Rationale: Refresh revocation alone does not invalidate already-issued stateless access tokens. Session version checks invalidate old access tokens immediately without requiring a token blacklist.

### D-012 - Record Password Change Time Separately

Decision: Add nullable `users.password_changed_at` for audit/readiness even though authorization uses `session_version`.

Rationale: The timestamp is useful for admin/security visibility while avoiding fragile JWT `iat` timestamp comparisons.

### D-013 - Force Web Logout Locally After Password Change

Decision: After a successful password change, the web app clears local session state and redirects to `/login` with a success message instead of calling `/auth/logout`.

Rationale: The backend has already revoked refresh tokens and invalidated the current access token, so a server logout call would be redundant and can fail with the intentionally stale token.

### D-014 - Clear the Memoryhive LocalStorage Namespace on Logout

Decision: Clearing session state removes all localStorage keys prefixed with `memoryhive.`.

Rationale: This satisfies clean login/logout behavior without deleting unrelated browser storage from other applications.

### D-015 - Centralize Web Session Cleanup in `AppShell`

Decision: Handle session-expired routing, library cleanup, idle refresh, and idle logout in `AppShell`.

Rationale: `AppShell` is the authenticated boundary that has access to auth state, navigation, and library store cleanup.

### D-016 - Refresh Idle Web Sessions Before Logging Out

Decision: Refresh the web library every 60 seconds while the user is idle, and sign out after 10 minutes of continuous inactivity.

Rationale: This matches the requested idle behavior while keeping active users unaffected by background refresh churn.

### D-017 - Treat Server Logout as Best Effort

Decision: Web logout always clears local auth state even if `/auth/logout` fails.

Rationale: Users must be signed out locally on demand, during password-change forced logout, and after session expiry regardless of network state.

### D-018 - Use One Mobile Forced-Logout Path

Decision: Mobile session expiry, idle timeout, explicit logout, and password-change logout all flow through one cleanup function in `AppStateProvider`.

Rationale: Mobile has both credentials and SQLite offline state, so cleanup must consistently clear SecureStore/localStorage, local database rows, memory state, and navigation.

### D-019 - Treat Mobile 401 Sync Errors as Session Expiry

Decision: If sync fails with API status `401`, mobile clears local session/data and redirects to login instead of showing a persistent sync error.

Rationale: Password changes, disabled accounts, and expired refresh tokens should not leave stale user data active on device.

### D-020 - Implement Mobile Idle Handling at the Provider Boundary

Decision: Track touch activity at the root provider and use a 60-second interval for idle sync plus 10-minute idle logout.

Rationale: The provider wraps all mobile routes and owns sync/session state, making it the least duplicated place for app-wide idle behavior.

### D-021 - Centralize Mobile Item Filtering Helpers

Decision: Add shared mobile helpers for summary, type, tag, and text filtering instead of duplicating filter logic in Home and Search.

Rationale: Mobile Library and Search need the same web-aligned semantics, and shared helpers keep future filter changes consistent.

### D-022 - Reuse Mobile FilterPills and TagPicker Components

Decision: Implement React Native `FilterPills` and `TagPicker` components and use them in capture, edit, home, and search workflows.

Rationale: The requested pill-plus-X pattern applies across mobile filters and tag editing, so a shared component reduces UI drift.

### D-023 - Include Archived Items for Filtered Mobile Views

Decision: Refresh mobile Home and Search with `includeArchived=true` where summary filters or archive state can be displayed.

Rationale: Archived records must be present locally for archive filters, restore workflows, and parity with web item visibility.

### D-024 - Use Native Alert Confirmations on Mobile

Decision: Use React Native `Alert.alert` for mobile favorite, archive, restore, delete, password-change, sign-out, and account-deletion confirmations.

Rationale: Native confirmations match platform behavior and avoid adding a custom modal system while still protecting destructive or state-changing actions.

### D-025 - Keep Mobile Account Actions in AppStateProvider

Decision: Expose account export and account deletion through `AppStateProvider` rather than calling account APIs directly from Settings.

Rationale: The provider owns sync, session state, SQLite cleanup, and navigation, so it is the correct boundary for account lifecycle side effects.

### D-026 - Use Expo Sharing for Mobile Account Exports

Decision: Add `expo-sharing` and share the downloaded account ZIP on native platforms; keep browser download behavior for mobile web preview.

Rationale: A downloaded ZIP in app cache is not user-accessible enough for account portability. Native sharing gives users a clear handoff target without building custom file management.

### D-027 - Make the Mobile Privacy Policy URL Configurable

Decision: Add `EXPO_PUBLIC_PRIVACY_POLICY_URL` and derive `/privacy` from the API origin only as a fallback.

Rationale: Store builds need an explicit public privacy URL, while local development should still have deterministic behavior without extra setup.

### D-028 - Keep Mobile Release Docs Active Under Goal 1

Decision: Create active mobile build, readiness, metadata, and privacy docs under `docs/GOAL-1/` instead of relying on archived release notes.

Rationale: Goal 1 explicitly asks for Android/iOS build-test docs and store-readiness gap documentation, and archived unchecked docs are not sufficient working artifacts.

### D-029 - Block the Merged Android Audio Permission

Decision: Add `android.blockedPermissions` for `android.permission.RECORD_AUDIO` in `mobile/app.json`.

Rationale: The app captures links, text, screenshots, and share-intent payloads but does not record audio. Removing unused sensitive permissions reduces store-review and privacy-disclosure risk.

### D-030 - Treat Store Readiness as Not Ready Until Artifacts Exist

Decision: Mark mobile store readiness as incomplete until EAS project identity, signing credentials, public privacy/deletion URLs, store assets, and real iOS/Android build artifacts are created and tested.

Rationale: Passing TypeScript, lint, unit tests, and Expo config inspection proves code health, not production submission readiness.

### D-031 - Host Privacy and Deletion Help in the Web App

Decision: Add `/privacy` and `/account/delete` as public React routes in the existing web app.

Rationale: The production web domain can serve the URLs required by mobile store forms without introducing a separate static site or service.

### D-032 - Support Web Account Deletion Through Sign-In Plus Fallback Contact

Decision: The public deletion page directs users to sign in and delete from Settings, and provides a support email fallback when the user cannot sign in.

Rationale: Backend account deletion requires identity verification. Web sign-in provides the strongest self-service proof, while fallback support covers users who cannot access the account.

### D-033 - Implement Mobile Organize From Synced Item Data First

Decision: Add mobile Organize as an item-backed view with status, type, and tag counts instead of adding mobile category CRUD in this slice.

Rationale: The current mobile offline database syncs item payloads only. Status, type, and tag organization can be implemented reliably from local item data, while category management requires a new category/tag sync contract.

### D-034 - Route Mobile Organize Selections Into Existing Filters

Decision: Organize tiles and rows navigate to the Home tab with `summary`, `type`, or `tag` route params.

Rationale: Home already owns mobile filter state and item display, so routing into that state avoids a second filtered-list implementation.

### D-035 - Make Admin Backup Execution Explicitly Configured

Decision: Add admin backup status by default, but only enable `POST /admin/backup/run` when `ADMIN_BACKUP_COMMAND` is set.

Rationale: Existing whole-system backups depend on Docker Compose, PostgreSQL dump tooling, MinIO mirroring, and host backup storage. Running arbitrary operational commands from the API must be an intentional deployment choice.

### D-036 - Reuse Existing Ops Backup Scripts

Decision: Keep `ops/backup.sh`, `ops/verify-backup.sh`, and `ops/restore.sh` as the canonical backup workflow, and let the admin API call a configured command rather than duplicating PostgreSQL/MinIO backup logic in Python.

Rationale: The scripts already back up both the database and object storage with checksums. Reusing them avoids divergent backup behavior.

### D-037 - Surface Backup Health From Filesystem Evidence

Decision: Admin backup status inspects backup directories for `postgres.dump`, `minio/`, `SHA256SUMS`, size, and timestamp.

Rationale: Admins need quick visibility into whether expected backup artifacts exist without restoring or downloading every backup from the dashboard.

### D-038 - Provide One Guarded Development Stack Wrapper

Decision: Add `ops/dev-stack.sh` for local stack lifecycle, validation, demo-data loading, smoke testing, and guarded cleanup.

Rationale: Goal 1 asks for scripts to start, stop, clean, load, and validate the app. A single wrapper keeps common Docker flows discoverable while reusing existing Compose, seed, and smoke tooling.

### D-039 - Gate Volume Cleanup With `CONFIRM_CLEAN`

Decision: Require `CONFIRM_CLEAN=memoryhive` before `ops/dev-stack.sh clean` deletes Docker volumes.

Rationale: Cleaning the development database and object storage is destructive, so it must be explicit even though the script is intended for local use.

### D-040 - Generate Knowledge Docs Deterministically

Decision: Add `scripts/generate_knowledge.py` as the source of truth for root and sub-project `Knowledge.md` files.

Rationale: Goal 1 asks for Knowledge files plus a regeneration script. Deterministic generation keeps agent context synchronized with project structure and commands.

### D-041 - Use Thin Agent Harness Adapters

Decision: Add `CLAUDE.md`, `CODEX.md`, and `ANTIGRAVITY.md` as short adapters that point to `AGENTS.md`, root `Knowledge.md`, and relevant sub-project Knowledge files.

Rationale: The repository should avoid maintaining divergent long-form instructions for each agent while still giving each tool an expected entry point.

### D-042 - Keep AGENTS.md Human-Focused

Decision: Keep `AGENTS.md` as a concise contributor guide and add only a short Knowledge Harness section.

Rationale: The earlier contributor-guide requirement asked for a compact document, while the generated Knowledge docs can hold agent-specific operational context.

### D-043 - Preserve Failed Processing Job History on Admin Retry

Decision: Admin retry of a failed processing job creates a new pending `ProcessingJob` with the existing retry helper instead of resetting the failed row.

Rationale: Failed jobs retain their error, attempt count, and timestamps for admin audit/debugging, while the worker continues to claim only pending jobs through the established queue path.

### D-044 - Keep Processing Queue Controls Under Admin APIs

Decision: Add system-wide processing queue listing and retry under `/api/v1/admin/processing/jobs`.

Rationale: Individual users already have item-scoped retry. Admins need cross-user operational visibility and controls without broadening user-owned item APIs.

### D-045 - Add Build and Deployment Assets In-Repo

Decision: Implement the Goal 1 build/deployment blueprint inside this repository instead of creating separate `memoryhive-build` and `memoryhive-deployments` repos.

Rationale: Memoryhive is currently a single application repository. Keeping build metadata, image manifests, Kubernetes config, and deployment commands together reduces coordination overhead while preserving the same concerns from the referenced templates.

### D-046 - Use JSON Config Plus Python Rendering for Kubernetes

Decision: Use JSON environment/profile/image-pin files with a standard-library Python Kubernetes renderer rather than Helm.

Rationale: The current service count is small, and the template recommends simple substitution for smaller systems. Python gives us conditional profile behavior, validation, and command orchestration without introducing a Helm dependency yet.

### D-047 - Pin Kubernetes Deployments to Immutable Image Tags

Decision: Tagged releases publish and manifest `<version>-<short_sha>` image refs, while also publishing `<version>` and `latest`.

Rationale: Kubernetes promotion should use reproducible image references. The extra tags preserve release convenience and local/operator discoverability.

### D-048 - Guard Kubernetes Mutations by Context and Delete Confirmation

Decision: `apply`, `upgrade`, `status`, `rollback`, and `delete` verify the expected kubectl context, and namespace deletion requires `CONFIRM_DELETE=memoryhive`.

Rationale: Deployment scripts can affect persistent data. Context matching and explicit delete confirmation reduce the chance of operating against the wrong cluster or deleting PVC-backed state accidentally.

### D-049 - Separate Analysis State From Processing State

Decision: Add first-class item analysis fields instead of overloading `processing_status`.

Rationale: Processing tracks extraction job health, while analysis tracks whether item content has been summarized/enriched. Separate state lets text captures, URL extraction, OCR, retries, and admin metrics be represented accurately.

### D-050 - Keep Temporal Optional Behind an Explicit Profile

Decision: Default local and production app flows keep the legacy database-backed worker, while `TEMPORAL_ENABLED=true` and the `temporal` profile route new analysis work through Temporal.

Rationale: The existing stack remains runnable without Temporal, and operators can adopt durable workflows deliberately once a Temporal server is available.

### D-051 - Use Item Versioning for Temporal Idempotency

Decision: Temporal workflow IDs include both `item_id` and `analysis_version`, and activities skip stale requests when the item version has changed.

Rationale: Item edits can happen while background workflows are queued or running. Versioned workflow IDs prevent duplicate starts and stale analysis overwrites.

### D-052 - Reuse the Existing Content Processor in Activities

Decision: Temporal activities call the same `ContentProcessor` used by the legacy worker instead of introducing a parallel analyzer.

Rationale: URL safety checks, OCR behavior, text normalization, optional enrichment, and summary fallback should stay consistent across worker backends.

### D-053 - Deploy Temporal Workers Separately From the Temporal Cluster

Decision: Docker Compose can run a local Temporal server/UI, but Kubernetes renders only Memoryhive `temporal-worker` and `temporal-scheduler` deployments that point at a configured Temporal address.

Rationale: Production Temporal is usually managed as shared infrastructure. Keeping the app manifests focused on Memoryhive processes avoids bundling stateful Temporal operations into this app deployment.

### D-054 - Keep Legacy Worker Analysis State Coherent

Decision: The database-backed processing worker now updates `analysis_status`, analysis errors, timestamps, and analysis metadata on claim, completion, failure, and retry.

Rationale: Temporal is optional. When the legacy worker processes links or screenshots, admin/user analysis metrics must not show completed items as indefinitely pending.

### D-055 - Add a Separate Automation Orchestrator App

Decision: Add `automation/` as a standalone Node package that coordinates existing seed, smoke, Docker, web Playwright, and mobile Playwright workflows.

Rationale: Goal 1 asks for automation as a separate app, but duplicating browser assertions would create drift. A root orchestrator satisfies repeatable execution while preserving canonical test scenarios in `frontend/e2e/` and `mobile/e2e/`.

### D-056 - Make Live E2E API Targets Configurable

Decision: Let frontend live Playwright and mobile Expo-web Playwright use `MEMORYHIVE_API_URL`, with the existing local API URL as the default.

Rationale: Automation needs to run against local Docker, Temporal profile, staging, or other API origins without editing test source files.

### D-057 - Treat Automation Cleanup as Stop-By-Default

Decision: `automation` cleanup stops Compose services by default and only delegates volume deletion to `ops/dev-stack.sh clean`, which still requires `CONFIRM_CLEAN=memoryhive`.

Rationale: Integration runs should be repeatable without destructive data loss. Volume cleanup remains available, but only through the existing guarded path.

### D-058 - Run Local Migrations Before App Processes

Decision: Add a one-shot Compose `migrate` service and make backend, worker, Temporal worker, and Temporal scheduler depend on it before startup.

Rationale: A healthy database connection is not enough when a retained Docker volume has an older schema. Startup should make schema readiness explicit before API or worker code touches migrated columns.

### D-059 - Reset Only Transient Rate-Limit Keys for Docker Automation

Decision: Docker automation calls `ops/dev-stack.sh rate-reset` after stack readiness, deleting only Redis keys that match `rate:*`.

Rationale: Full integration runs perform several register/login flows and are often retried within the same minute. Clearing limiter counters makes the run deterministic without deleting database, MinIO, or other persistent development volumes.

### D-060 - Submit Save Actions Before Pending-Tag Blur Reflow

Decision: Web and Expo-web save actions submit on pointer/press start when pending tag input can commit on blur, while still preserving normal keyboard/click activation and native mobile press behavior.

Rationale: Committing comma-separated tags on blur can add pills and shift layout before the click/press event fires. Submitting before that reflow keeps the user action reliable and merges pending tag text into the saved payload.

### D-061 - Make Support a Public Store-Readiness Route

Decision: Add `/support` as a public React route alongside `/privacy` and `/account/delete`.

Rationale: Apple and Google store submissions need a stable support URL. Hosting it in the existing web app keeps compliance pages together while still requiring production deployment and real operator contact details before submission.

### D-062 - Track Goal 1 Completion With a Separate Audit Artifact

Decision: Add `docs/GOAL-1/COMPLETION_AUDIT.md` instead of marking Goal 1 complete from implementation logs alone.

Rationale: The implementation log records completed slices, but final completion depends on proving every requirement against current evidence and separating repository-local work from external release/account dependencies.

### D-063 - Expose Support URL in Mobile Settings

Decision: Add `EXPO_PUBLIC_SUPPORT_URL` to mobile configuration and show it from Settings, falling back to `/support` derived from the API origin.

Rationale: Store builds need an explicit support URL, while local development should remain usable without extra configuration.

### D-064 - Make Mobile Store Readiness Mechanically Checkable

Decision: Add `npm run store:check` as a non-strict readiness report with `-- --strict` available for release gates.

Rationale: Current submission blockers include external account credentials and artwork. A non-strict local report keeps those blockers visible without breaking normal development commands, while strict mode can fail a release pipeline once the project is closer to submission.

### D-065 - Generate Store Artwork Deterministically

Decision: Generate the mobile store icon source and Google Play feature graphic from source-controlled HTML/CSS rendered through Playwright and normalized with `pngjs`.

Rationale: The repo needs repeatable, inspectable branded assets without depending on opaque external design files. RGB PNG normalization keeps the generated feature graphic aligned with store upload constraints.

### D-066 - Use Seeded Expo-Web Store Screenshots for Local Handoff

Decision: Capture the current screenshot pack from Expo web preview backed by refreshed engineer demo data, while documenting native-device replacement after signed builds if required.

Rationale: Signed native builds and physical devices are external release steps. Seeded Expo-web captures make local store-size assets repeatable now and keep the remaining native-review risk explicit.

### D-067 - Gate Mobile App Tabs Until Local State Is Ready

Decision: Render a loading state from the Expo app tab layout until `AppStateProvider` finishes session and SQLite initialization.

Rationale: Direct routes such as `/home` can render before local tables exist in Expo web. Gating tabs avoids table initialization races and keeps automated screenshots free of development error overlays.

### D-068 - Keep AGENTS.md as Both Guide and Harness Entry

Decision: Preserve `AGENTS.md` as a concise contributor guide while including a short instruction to read root and area `Knowledge.md` files before changes.

Rationale: A standalone contributor guide satisfies repository onboarding, but Goal 1 also requires agent wiring into the generated Knowledge harness. The combined file avoids divergent top-level instructions.

### D-069 - Treat Store Manifests as Release Handoff Metadata

Decision: Include dimensions, purpose/screen context, platform/form-factor, and short alt text in generated mobile store asset manifests, and validate those fields in `store:check`.

Rationale: Store operators need more than image filenames when filling App Store and Play Console forms. Keeping metadata generated and checked prevents stale handoff notes from drifting away from the actual assets.

### D-070 - Generate a Structured Mobile Store Submission Packet

Decision: Add `npm run store:submission` to generate a JSON submission packet and Markdown handoff from the app config, production env template, and generated store asset manifests.

Rationale: Store operators need one deterministic source for App Store and Google Play forms. Generating the packet prevents release copy, URL placeholders, asset metadata, privacy notes, and blocker lists from drifting across separate docs.

### D-071 - Separate Apple Subtitle From Google Short Description

Decision: Use `Capture. Tag. Find.` as the App Store subtitle, keep the longer Google Play short description, and validate both limits in `store:check`.

Rationale: Apple and Google use different short-copy limits. Separate fields keep Apple metadata within the subtitle limit while preserving more descriptive Google Play copy.

### D-072 - Configure Public Support Email at Build Time

Decision: Use `VITE_SUPPORT_EMAIL` as the shared frontend support contact for `/support`, `/privacy`, and `/account/delete`, and keep `store:check` blocked while the production template still contains a placeholder email.

Rationale: Store review needs a real public support contact, but the repo should not hard-code an operator-owned address. Build-time configuration keeps public pages, Docker images, generated store packets, and readiness checks aligned.

### D-073 - Gate Frontend Release Images on Real Support Email

Decision: Require GitHub repository variable `VITE_SUPPORT_EMAIL` before the release workflow publishes frontend images, and validate that `store:check` rejects a hard-coded placeholder release build arg.

Rationale: Vite embeds public env vars at build time. A tagged frontend image built with `support@memoryhive.example.com` would remain wrong even if production Compose later has the right value, so the release pipeline must fail before image publication when the real contact is missing.

### D-074 - Keep Mobile Organization Records Server-Owned

Decision: Mobile category and managed-tag records are fetched from the existing server endpoints and refreshed after sync; only item payloads remain in the offline mutation queue.

Rationale: Category/tag metadata has user-owned server uniqueness rules and no existing change-feed contract. Keeping organization CRUD online-only avoids inventing a second sync protocol while still allowing offline item capture and category/tag filtering from cached items.

### D-075 - Scrub Local Item State After Organization Deletes

Decision: After a server-accepted category or tag delete, mobile clears matching references from cached item payloads and pending item mutation payloads.

Rationale: Without scrubbing, an offline-created or queued item update could reapply a deleted category or recreate a deleted tag during the next sync. The local cache should reflect the accepted organization delete immediately and prevent stale queued payloads from undoing it.

### D-076 - Cover Mobile Category Parity in E2E

Decision: Extend the mobile Expo-web Playwright workflow to create a category, assign one captured note to it, create an uncategorized control note, and verify the Library category filter hides the control item.

Rationale: Unit tests cover category filtering helpers, but the Goal 1 parity requirement also needs evidence that the mobile UI wires Organize, Capture, and Library filtering together correctly.

### D-077 - Track Store Review Access Without Committing Passwords

Decision: Add `STORE_REVIEW_ACCOUNT_EMAIL` to release handoff configuration and make `store:check` block while it is still a placeholder, but keep the reviewer password as an out-of-band store-console entry.

Rationale: Apple and Google review need credentials for authenticated apps. The reviewer account email is useful release metadata, but committing a real temporary password in generated JSON or Markdown would create an avoidable credential leak.

### D-078 - Require Native Build Evidence Beyond Artifact Presence

Decision: Split the store-readiness build gate into separate iOS artifact, Android artifact, iOS device-test, and Android target/permission evidence checks backed by `mobile/builds/native-artifacts.json`.

Rationale: A single `.ipa`, `.aab`, or `.apk` file does not prove that both platforms were built, tested, and checked against Google Play target API and sensitive-permission expectations. The evidence manifest makes final release validation explicit while keeping large signed artifacts out of git.

### D-079 - Treat Production Store URLs as Blocking Release Config

Decision: Make placeholder mobile production API, privacy, and support URLs blockers in `store:check`, and allow release environment values to override `.env.production.example` for checker and submission-packet generation.

Rationale: Store submission cannot proceed with example-domain URLs, but operators should not have to edit source-controlled templates to generate a final handoff. Environment overrides keep real release config out of git while making the readiness gate accurately reflect submission blockers.

### D-080 - Require Store Packet Config to Match Checked Release Env

Decision: Make `store:check` compare `mobile/store-assets/submission-packet.json` against the production URLs, support email, and reviewer email resolved from the current release environment.

Rationale: A readiness check that accepts real environment overrides while the handoff packet still contains placeholder values can mislead a store submission. Requiring packet/config consistency forces operators to regenerate the packet with the exact environment they intend to submit.

### D-081 - Require Platform-Specific Native Artifact Evidence

Decision: Native build evidence must point to non-empty platform artifacts under `mobile/builds/` using `.ipa` for iOS and `.aab` or `.apk` for Android, and each platform must list at least two tested device records.

Rationale: A stray file elsewhere in the repo or a single ad hoc device run is weak release evidence. Platform-specific paths and multi-device records better match the App Store and Google Play readiness risk, especially because the app supports tablet layouts and platform-specific share/image-picker behavior.

### D-082 - Reject Non-Public Release URLs and Invalid Store Emails

Decision: `store:check` treats production URL values as valid only when they are public HTTPS routes matching `/api/v1`, `/privacy`, and `/support`, and treats support/reviewer emails as valid only when they are syntactically valid non-placeholder addresses on non-reserved domains.

Rationale: Store review cannot use localhost, private IP, reserved-domain, or wrong-path URLs, and malformed contact emails are operationally equivalent to missing contact metadata. Validating these shapes locally reduces the chance of producing a handoff packet that looks complete but cannot be used in App Store Connect or Play Console.

### D-083 - Load Release Store Config From an Access-Controlled Env File

Decision: `store:submission` and `store:check` accept `--release-env-file <path>` and resolve release config with shell environment values first, then env-file values, then `.env.production.example` placeholders.

Rationale: Store operators need a repeatable final handoff path without editing source-controlled templates or committing real contact/reviewer metadata. Keeping shell environment precedence also lets CI or one-off commands override file values deliberately.

### D-084 - Keep Store Env File Flags Separate From Node Runtime Flags

Decision: Expose only `--release-env-file` for the mobile store scripts, reject native Node `--env-file` use before store config is read, and cover the shared parser with Vitest instead of supporting an undocumented alias.

Rationale: Recent Node versions treat `--env-file` as a runtime option, which can be consumed before the script sees it. A project-specific flag avoids ambiguous invocation behavior, and focused parser tests keep the release handoff contract stable.

### D-085 - Share Store Release Config Resolution Between Store Scripts

Decision: Move mobile store release URL, contact, reviewer-account, and validation helpers into `mobile/scripts/store-release-config.mjs`, and make both `store:submission` and `store:check` consume that resolver.

Rationale: The generated submission packet and readiness checker must agree on shell, release-env-file, template, and fallback precedence. A shared resolver prevents one script from accepting or generating release metadata that the other script would interpret differently.

### D-086 - Make Store Privacy Disclosures Explicit Release Config

Decision: Add `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` as non-secret release handoff values, include them in the generated mobile store submission packet, and make `store:check` validate allowed values plus AI-enrichment consistency.

Rationale: Apple App Privacy and Google Play Data safety answers should not depend on an informal checklist reminder. Explicit release values keep production AI/automation enrichment and telemetry assumptions visible, repeatable, and aligned with the generated handoff packet.

### D-087 - Unit-Test Native Build Evidence Rules Outside The CLI

Decision: Extract native build evidence path, artifact-extension, build-ID, tested-device, Android target SDK, and `RECORD_AUDIO` rules into `mobile/scripts/native-build-evidence.mjs`, and keep `store:check` as the reporting layer.

Rationale: Signed artifact and native test evidence remain external release inputs, but the repository-owned interpretation of that evidence should be testable. A pure validator module prevents future checker edits from weakening platform-specific evidence requirements.

### D-088 - Unit-Test Submission Packet Rules Outside The CLI

Decision: Extract mobile store submission-packet shape, release-config matching, review-password safety, and copy-length checks into `mobile/scripts/store-submission-packet.mjs`, and keep `store:check` responsible for reporting those results.

Rationale: The handoff packet is the artifact operators copy into App Store Connect and Play Console. Its structure, config alignment, and out-of-band password handling should be tested directly instead of depending only on inline CLI checks.

### D-089 - Unit-Test Store Asset And Screenshot Rules Outside The CLI

Decision: Extract mobile store PNG parsing, asset manifest validation, expected screenshot dimensions, and screenshot manifest validation into `mobile/scripts/store-asset-readiness.mjs`, and make malformed expected screenshot PNGs count as invalid store assets.

Rationale: Store artwork and screenshots are release-blocking artifacts. Their expected sizes, RGB PNG constraints, and handoff metadata should be tested directly so future checker edits cannot silently accept malformed or stale generated files.

### D-090 - Require Store Console Evidence Before Strict Release Readiness

Decision: Add `mobile/store-assets/store-console-evidence.example.json` and validate final App Store Connect, Google Play Console, and privacy verification evidence through `mobile/scripts/store-console-evidence.mjs`.

Rationale: Store forms and final privacy answers are external release actions, but the repository should still define what evidence proves they are complete. A checked evidence file prevents a strict readiness report from passing only because local assets and build artifacts exist.

### D-091 - Require EAS Release Evidence Before Strict Release Readiness

Decision: Add `mobile/builds/eas-release-evidence.example.json` and validate EAS project identity, production environment setup, iOS signing, Android signing, and submit setup through `mobile/scripts/eas-release-readiness.mjs`.

Rationale: EAS project ownership, signing credentials, and production environment configuration are external account actions. A non-secret evidence manifest makes those actions auditable without committing signing material, service-account keys, or release secrets.

### D-092 - Separate Repository And Release Readiness Gates

Decision: Classify mobile readiness blockers as `repository` or `release`. Run `store:check:ci` in pull-request CI to fail repository defects while reporting external prerequisites, and retain `store:check -- --strict` as the final gate that fails on either class.

Rationale: Missing store accounts, credentials, and signed artifacts are expected before release and should not disable everyday CI. Repository-owned regressions in config, docs, assets, manifests, or generated packets must still fail immediately instead of hiding among accepted external blockers.

### D-093 - Select Shadow Styles Per Runtime Platform

Decision: Define shared mobile shadows with `Platform.select`, using CSS `boxShadow` for React Native Web and native shadow/elevation properties for iOS and Android.

Rationale: React Native Web deprecates legacy `shadow*` properties, while native platforms still benefit from their platform-specific rendering behavior. Selecting at module load keeps rendered styles warning-free without weakening native appearance.

### D-094 - Validate Generated Store Packets Without Rewriting Them

Decision: Add `store:submission:check` to compare expected packet content directly with both committed generated files, and run it in CI before the repository readiness gate.

Rationale: Generating files and then running `git diff` does not reliably detect outputs deleted from source control because regenerated files can be untracked. A read-only byte comparison catches missing, stale, and deleted outputs, avoids CI mutation, and is independently testable.

### D-095 - Queue Native Builds Manually Without Store Submission

Decision: Add a manually dispatched GitHub workflow for `ios`, `android`, or `all` production EAS builds. Require token/project/profile preflight, explicit EAS environments, frozen credentials, repository release gates, and a JSON request artifact; do not wait for completion or auto-submit.

Rationale: Native build initiation should be repeatable once account setup is complete, but signing changes and store submission are consequential external actions. A queue-only workflow provides auditable build IDs while keeping credential creation, build monitoring, device testing, and submission under deliberate operator control.

### D-096 - Keep Account Deletion As One Strong Confirmation Modal

Decision: Treat the web account-deletion modal as the confirmation boundary because it requires both the current password and exact typed `DELETE`; do not stack a second generic confirmation dialog. Add component coverage across the destructive workflows instead.

Rationale: The existing modal exceeds a yes/no confirmation while remaining accessible and understandable. A nested dialog would add friction and focus-management risk without improving intent verification; regression tests provide the missing assurance.

### D-097 - Separate Chronology From Goal Status Handoff

Decision: Keep `CODEX-GOAL-1.MD` as the append-only implementation chronology
and maintain an indexed summary, numbered requirement matrix, and current-state report under
`docs/GOAL-1/Goal Status/` for continuation and completion decisions.

Rationale: Forty-plus implementation slices preserve useful evidence but obscure
the current verdict. A separate handoff package makes repository completion,
external blockers, ownership, validation results, and the next action explicit
without rewriting historical records.
