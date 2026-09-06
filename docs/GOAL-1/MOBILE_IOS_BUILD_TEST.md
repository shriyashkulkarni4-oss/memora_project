# Mobile iOS Build and Test

Last checked: 2026-09-06.

## Current State

- Expo SDK: 54.0.0.
- App ID: `com.codingmonkeylabs.memoryhive`.
- EAS profiles explicitly select matching `development`, `preview`, and `production` environments in `mobile/eas.json`.
- `.github/workflows/mobile-eas-build.yml` can queue a guarded production iOS build after EAS initialization and secret setup.
- `mobile/app.json` has `ios.supportsTablet=true`, photo-library permission text, and `ITSAppUsesNonExemptEncryption=false`.
- No `.ipa` artifact, native build evidence manifest, or EAS `projectId` is committed yet.

## Prerequisites

- Apple Developer Program membership with access to certificates, identifiers, and provisioning profiles.
- Expo account and EAS CLI: `npx eas-cli@latest login`.
- Public HTTPS production API reachable from devices at `/api/v1`.
- Public web build deployed with `VITE_SUPPORT_EMAIL` set to the operator's real support address.
- Dedicated store-review account created; set `STORE_REVIEW_ACCOUNT_EMAIL` and keep the password out of source control.
- EAS environment variables configured for the production profile with real public values:
  - `EXPO_PUBLIC_API_URL=https://YOUR-DOMAIN/api/v1`
  - `EXPO_PUBLIC_PRIVACY_POLICY_URL=https://YOUR-DOMAIN/privacy`
  - `EXPO_PUBLIC_SUPPORT_URL=https://YOUR-DOMAIN/support`
  - `VITE_SUPPORT_EMAIL=support@YOUR-DOMAIN`
  - `STORE_REVIEW_ACCOUNT_EMAIL=reviewer@YOUR-DOMAIN`
  - `STORE_EXTERNAL_AI_PROCESSING=none` or `self_hosted` or `third_party`
  - `STORE_PRODUCTION_TELEMETRY=none` or `analytics` or `crash_reporting` or `analytics_and_crash_reporting` or `other`
- `mobile/builds/eas-release-evidence.json` created from the example after EAS project, production environment, signing, and submit setup are complete.

## Build Commands

```bash
cd mobile
npm ci
npm run typecheck
npm run lint
npm test
npm run store:assets
npm run store:screenshots
npm run store:submission -- --release-env-file ../.env.production
npm run store:check -- --release-env-file ../.env.production --strict
npx expo config --type public
npx eas-cli@latest init
npx eas-cli@latest build --platform ios --profile development
npx eas-cli@latest build --platform ios --profile preview
npx eas-cli@latest build --platform ios --profile production
```

For GitHub Actions, add `EXPO_TOKEN` as a repository secret and manually run
`Mobile EAS Build` with `platform=ios`. The workflow preflight requires a real
committed EAS project ID, checks repository release artifacts, freezes existing
credentials, queues without waiting, and uploads the JSON build request. It
does not submit the build to App Store Connect.

After EAS init, production environment setup, and iOS signing setup, copy
`mobile/builds/eas-release-evidence.example.json` to
`mobile/builds/eas-release-evidence.json` and record the project ID, production
environment, Apple team ID, iOS credentials, production profile, and submit
setup without adding secret values.

Use `eas device:create` before an ad hoc device build when testing on physical iPhones or iPads.
After the production build, copy `mobile/builds/native-artifacts.example.json`
to `mobile/builds/native-artifacts.json` and record the iOS EAS build ID,
the non-empty `.ipa` artifact path under `mobile/builds/`, and at least two
tested iPhone/iPad devices.

## Device Test Checklist

- Register, login, logout, password change, and forced re-login.
- Capture text, links, screenshots, and inbound share-extension content.
- Search by query, type, summary state, and tag.
- Edit item title, notes, favorite, archive, restore, and tags.
- Confirm offline capture, reconnect sync, and conflict-safe update behavior.
- Export account data through the native share sheet.
- Delete account and verify local data plus credentials are removed.
- Verify iPhone and iPad layouts because tablet support is enabled.
- Confirm `mobile/builds/native-artifacts.json` records at least two tested devices and the production `.ipa` path under `mobile/builds/`.

## Submit

After a production build passes TestFlight checks:

```bash
npx eas-cli@latest submit --platform ios --latest
```

Complete App Store Connect metadata, screenshots, privacy answers, review credentials, review notes, and export-compliance answers before App Review.

## Sources

- Expo EAS Build: https://docs.expo.dev/build/introduction/
- Expo CI builds: https://docs.expo.dev/build/building-on-ci/
- Expo iOS production build: https://docs.expo.dev/tutorial/eas/ios-production-build/
- Expo submit: https://docs.expo.dev/deploy/submit-to-app-stores/
