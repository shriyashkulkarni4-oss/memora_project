# Mobile Store Metadata Draft

Last checked: 2026-09-06.

## App Identity

- App name: Memoryhive
- Bundle ID / package: `com.codingmonkeylabs.memoryhive`
- Category: Productivity
- Age rating target: general productivity app; complete Apple and Google questionnaires before submission.
- Support URL: `https://memoryhive.example.com/support` (placeholder route shape; replace with public HTTPS `/support` before submission)
- Privacy URL: `https://memoryhive.example.com/privacy` (placeholder route shape; replace with public HTTPS `/privacy` before submission)
- Account deletion URL: `https://memoryhive.example.com/account/delete` (route exists; deploy before Google Play submission)
- Store review account email: `reviewer@memoryhive.example.com` (placeholder; replace `STORE_REVIEW_ACCOUNT_EMAIL` with a valid reviewer address before submission)
- External AI processing disclosure: `STORE_EXTERNAL_AI_PROCESSING=none` by default; set to `self_hosted` or `third_party` if production enrichment sends user content to an AI/automation processor.
- Production telemetry disclosure: `STORE_PRODUCTION_TELEMETRY=none` by default; update if production adds analytics, crash reporting, or related tooling.

## Short Copy

App Store subtitle:

> Capture. Tag. Find.

Google Play short description:

> Capture links, screenshots, and notes into a searchable offline-first library.

Promotional text:

> Save what matters, organize it with tags, and find it again across web and mobile.

## Full Description

Memoryhive is a personal capture and recall app for links, screenshots, and text notes. Save items from your device, add tags and notes, search locally while offline, and sync when you reconnect.

Key features:
- Capture links, screenshots, and text notes.
- Search by query, item type, status, and tag.
- Edit titles, notes, and tags after capture.
- Favorite, archive, restore, and delete items with confirmation.
- Keep a local offline library and sync changes later.
- Export account data and delete your account from Settings.

## Keywords

memory, capture, bookmarks, notes, screenshots, knowledge, offline, search, tags, productivity

## Screenshot Plan

- iPhone: Home/library filters, capture screen, item detail edit, search results, settings privacy/export/delete.
- iPad: Library/search layout and item detail.
- Android phone: Same sequence as iPhone, including Android share-intent capture.
- Android tablet: Library/search and settings.
- Google Play feature graphic: generated at `mobile/store-assets/feature-graphic.png` with Memoryhive brand, library UI, and the phrase “Capture. Tag. Find.”

## Generated Assets

- Store icon source: `mobile/store-assets/icon-1024.png` (`1024x1024`, RGB PNG).
- Google Play feature graphic: `mobile/store-assets/feature-graphic.png` (`1024x500`, RGB PNG).
- Asset manifest: `mobile/store-assets/manifest.json` with dimensions, purpose, and alt text.
- Asset readiness rules are shared in `mobile/scripts/store-asset-readiness.mjs` and covered by `mobile/tests/store-asset-readiness.test.mjs`.
- Submission packet: `mobile/store-assets/submission-packet.json` and `docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md`.
- Regenerate with `cd mobile && npm run store:assets`.
- Refresh the submission packet with `cd mobile && npm run store:submission`.

## Generated Screenshots

The current screenshot pack is captured from Expo web preview with seeded engineer demo data:

- `mobile/store-assets/screenshots/iphone-01-library.png` (`1290x2796`, RGB PNG).
- `mobile/store-assets/screenshots/android-phone-02-search.png` (`1080x1920`, RGB PNG).
- `mobile/store-assets/screenshots/ipad-03-library.png` (`2048x2732`, RGB PNG).
- `mobile/store-assets/screenshots/android-tablet-04-organize.png` (`1600x2560`, RGB PNG).
- Screenshot manifest: `mobile/store-assets/screenshots/manifest.json` with platform, form-factor, dimensions, screen, and alt text.
- `npm run store:check` treats missing, malformed, wrong-size, or non-RGB expected screenshots as blockers.
- Refresh with `cd mobile && npm run store:screenshots` while the local backend is running.

Replace these with native-device captures after signed builds if native UI differs or store review requires screenshots from native binaries.

## Alt Text Drafts

- Store icon: Memoryhive app icon with a teal personal-library mark.
- Feature graphic: Memoryhive branded graphic showing a searchable library for links, screenshots, and notes.
- iPhone library: Memoryhive iPhone library showing saved items, favorite counts, tags, and link cards.
- Android phone search: Memoryhive Android phone search results for FastAPI with saved filters and tags.
- iPad library: Memoryhive iPad library with synced seeded content and reusable tag filters.
- Android tablet organize: Memoryhive Android tablet organize view showing item counts, types, categories, and tags.

## Review Notes

Provide a seeded demo account with no real personal data:

- Email: use `STORE_REVIEW_ACCOUNT_EMAIL`.
- Password: generate a temporary password and enter it directly in App Store Connect and Play Console; do not commit it.
- Notes: mention offline mode, share intent, account export, and account deletion paths.

## Missing Assets and Metadata

- Valid operator support address via `VITE_SUPPORT_EMAIL` and final store-form contact details.
- Valid dedicated reviewer account email via `STORE_REVIEW_ACCOUNT_EMAIL`.
- Final privacy disclosures via `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY`.
- Final localized description, keywords, release notes, and marketing URL.

## Sources

- Apple product page guidance: https://developer.apple.com/app-store/product-page/
- Apple App information reference: https://developer.apple.com/help/app-store-connect/reference/app-information/app-information/
- Apple screenshot specifications: https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/
- Google Play preview assets: https://support.google.com/googleplay/android-developer/answer/9866151
- Expo app config icon guidance: https://docs.expo.dev/versions/latest/config/app/
- Expo submit workflow: https://docs.expo.dev/deploy/submit-to-app-stores/
