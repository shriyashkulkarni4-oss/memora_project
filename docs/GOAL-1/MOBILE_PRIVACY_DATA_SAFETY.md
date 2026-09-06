# Mobile Privacy and Data Safety Draft

Last checked: 2026-09-06.

This is an engineering draft for Apple App Privacy and Google Play Data safety. Product, legal, and operations owners must verify it against the production backend, logging, analytics, support, and retention practices before submission.

## Data Inventory

Memoryhive accounts collect or process:

- Account data: email, optional name, password during authentication, user ID.
- User content: links, screenshots/images, text notes, titles, descriptions, tags, categories, metadata, extracted text, OCR output, and summaries.
- App activity: capture, edit, archive, favorite, delete, sync, and processing status timestamps.
- Diagnostics/operations: request IDs, API logs, error details, rate-limit events, backup records, and cleanup audit records.

No advertising SDK, third-party analytics SDK, precise location, contacts, calendar, microphone, camera capture, or payment data is currently implemented in the mobile app.

## Release Disclosure Configuration

`npm run store:submission` copies the following non-secret declarations into the App Store / Google Play handoff packet, and `npm run store:check` validates them:

- `STORE_EXTERNAL_AI_PROCESSING`: `none`, `self_hosted`, or `third_party`. Use `self_hosted` or `third_party` if production enables `OLLAMA_BASE_URL` or `N8N_WEBHOOK_URL`; the checker blocks enrichment endpoints paired with `none`.
- `STORE_PRODUCTION_TELEMETRY`: `none`, `analytics`, `crash_reporting`, `analytics_and_crash_reporting`, or `other`.

The repository default is `none` for both. Product, legal, and operations owners must update these values in the release environment if production adds AI processors, analytics, crash reporting, or support tooling outside this repo.

After Apple App Privacy and Google Play Data safety are completed, record final
verification in `mobile/store-assets/store-console-evidence.json` using the
example template. The evidence must match the release environment disclosure
values and must not include reviewer passwords.

## Apple App Privacy Draft

Likely data types:

- Contact Info: email address and optional name.
- User Content: photos/screenshots, text notes, links, tags, categories, and generated summaries.
- Identifiers: internal user ID.
- Usage Data or Diagnostics: only if production logs are treated as product interaction or crash/error diagnostics.

Suggested purposes:

- App Functionality
- Account Management
- Product Personalization only if summaries/search organization are considered personalized processing.

Tracking:

- Mark tracking as no unless a future analytics, ads, or cross-app tracking SDK is added.

## Google Play Data Safety Draft

Likely collected data categories:

- Personal info: email address and name.
- Photos and videos or files and docs: user-selected screenshots/images.
- App activity: app interactions and in-app search/capture activity if retained in logs.
- App info and performance or diagnostics: crash/error logs if enabled in production.

Security answers:

- Data is encrypted in transit when production uses HTTPS.
- Users can request deletion; mobile now provides in-app account deletion.
- Account deletion removes server-owned user data and uploaded assets through the backend deletion lifecycle.

## Current Blocking Gaps

- Deploy the public `/privacy`, `/account/delete`, and `/support` routes on the production domain.
- Replace placeholder `VITE_SUPPORT_EMAIL` with a valid operator support address.
- Replace placeholder `STORE_REVIEW_ACCOUNT_EMAIL` with a valid dedicated reviewer account that contains no real personal data.
- Configure public HTTPS `EXPO_PUBLIC_PRIVACY_POLICY_URL` and `EXPO_PUBLIC_SUPPORT_URL` routes for production mobile builds.
- Review `docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md` and replace draft placeholders before copying answers into store consoles.
- Confirm retention windows for server logs, backups, cleanup audit records, and object-storage deletion.
- Set `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` to match the production backend and operations stack before regenerating the submission packet.
- Complete Apple App Privacy and Google Data safety forms from verified production behavior.
- Record the final privacy and store-console evidence in `mobile/store-assets/store-console-evidence.json`.

## Sources

- Apple App Privacy: https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/
- Apple privacy policy review notes: https://developer.apple.com/distribute/app-review/
- Google Data safety: https://support.google.com/googleplay/android-developer/answer/10787469
- Google account deletion: https://support.google.com/googleplay/android-developer/answer/13327111
- Google User Data policy: https://support.google.com/googleplay/android-developer/answer/10144311
