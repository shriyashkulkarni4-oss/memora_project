# Mobile Store Submission Packet

Status: draft handoff generated from `npm run store:submission`.

## App Identity

| Field | Value |
| --- | --- |
| Name | Memoryhive |
| Version | 1.0.0 |
| iOS bundle ID | `com.codingmonkeylabs.memoryhive` |
| Android package | `com.codingmonkeylabs.memoryhive` |
| Category | Productivity |
| Privacy URL | https://memoryhive.example.com/privacy |
| Support URL | https://memoryhive.example.com/support |
| Account deletion URL | https://memoryhive.example.com/account/delete |
| Support email | support@memoryhive.example.com |

## Store Copy

App Store subtitle:

> Capture. Tag. Find.

Google Play short description:

> Capture links, screenshots, and notes into a searchable offline-first library.

Promotional text:

> Save what matters, organize it with tags, and find it again across web and mobile.

Full description:

Memoryhive is a personal capture and recall app for links, screenshots, and text notes. Save items from your device, add tags and notes, search locally while offline, and sync when you reconnect.

Key features:

- Capture links, screenshots, and text notes.
- Search by query, item type, status, and tag.
- Edit titles, notes, and tags after capture.
- Favorite, archive, restore, and delete items with confirmation.
- Keep a local offline library and sync changes later.
- Export account data and delete your account from Settings.

Keywords:

memory, capture, bookmarks, notes, screenshots, knowledge, offline, search, tags, productivity

## Assets

- Store icon: `mobile/store-assets/icon-1024.png` (1024x1024) - Memoryhive app icon with a teal personal-library mark.
- Google Play feature graphic: `mobile/store-assets/feature-graphic.png` (1024x500) - Memoryhive branded graphic showing a searchable library for links, screenshots, and notes.

Screenshots:

- `iphone-01-library.png` (ios iphone, 1290x2796) - Memoryhive iPhone library showing saved items, favorite counts, tags, and link cards.
- `android-phone-02-search.png` (android phone, 1080x1920) - Memoryhive Android phone search results for FastAPI with saved filters and tags.
- `ipad-03-library.png` (ios ipad, 2048x2732) - Memoryhive iPad library with synced seeded content and reusable tag filters.
- `android-tablet-04-organize.png` (android tablet, 1600x2560) - Memoryhive Android tablet organize view showing item counts, types, categories, and tags.

## Privacy And Data Safety

Apple data types:

- Contact Info: email address and optional name.
- User Content: photos/screenshots, text notes, links, tags, categories, and generated summaries.
- Identifiers: internal user ID.
- Usage Data or Diagnostics: only if production logs are treated as product interaction or crash/error diagnostics.

Google data categories:

- Personal info: email address and name.
- Photos and videos or files and docs: user-selected screenshots/images.
- App activity: app interactions and in-app search/capture activity if retained in logs.
- App info and performance or diagnostics: crash/error logs if enabled in production.

Tracking: No, unless a future analytics, ads, or cross-app tracking SDK is added.

Security: Data is encrypted in transit when production uses HTTPS. Account deletion removes server-owned user data and uploaded assets through the backend lifecycle.

External AI processing: none

No external AI processor is declared for store privacy answers.

Production telemetry: none

No production analytics or crash-reporting tooling is declared in this release handoff.

## Review Access

App Store Connect:

- Email: `reviewer@memoryhive.example.com`
- Password: Do not commit. Generate a temporary password and enter it directly in App Store Connect.
- Notes: Mention offline mode, share intent, account export, and account deletion paths.

Play Console:

- Email: `reviewer@memoryhive.example.com`
- Password: Do not commit. Generate a temporary password and enter it directly in Play Console.
- Notes: Use the same reviewer account as App Store Connect when possible.

## Release Blockers

- Run EAS init and commit the generated extra.eas.projectId.
- Configure public HTTPS /api/v1, /privacy, and /support URL values plus a valid VITE_SUPPORT_EMAIL in the release environment.
- Create a dedicated store-review account and replace STORE_REVIEW_ACCOUNT_EMAIL with its valid email.
- Configure EAS production environment variables and signing credentials.
- Create mobile/builds/eas-release-evidence.json from the example after EAS project, environment, and signing setup are complete.
- Create Apple Developer and Google Play app records.
- Produce a signed iOS .ipa and record it in mobile/builds/native-artifacts.json.
- Produce a signed Android .aab or .apk and record it in mobile/builds/native-artifacts.json.
- Record native-device test evidence for iOS and Android in mobile/builds/native-artifacts.json.
- Verify Android targetSdkVersion >= 36 and RECORD_AUDIO absence from the final merged manifest.
- Complete Apple App Privacy and Google Play Data safety forms from verified production behavior.
- Create mobile/store-assets/store-console-evidence.json from the example after App Store Connect and Play Console fields are complete.
- Replace Expo-web screenshots with native-device captures after signed builds if native UI differs or store review requires native screenshots.
