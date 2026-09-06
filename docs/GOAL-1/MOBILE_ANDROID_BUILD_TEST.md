# Mobile Android Build and Test

Last checked: 2026-09-06.

## Current State

- Expo SDK: 54.0.0.
- Android package: `com.codingmonkeylabs.memoryhive`.
- `android.versionCode=1`; production EAS builds use remote auto-increment.
- `android.blockedPermissions` removes `android.permission.RECORD_AUDIO` from the final merged manifest.
- EAS profiles explicitly select matching development, preview, and production environments.
- `.github/workflows/mobile-eas-build.yml` can queue a guarded production Android build after EAS initialization and secret setup.
- No `.aab`, `.apk`, native build evidence manifest, EAS `projectId`, Play app, or Play service-account setup is committed.

## Prerequisites

- Google Play Developer account.
- Expo account and EAS CLI: `npx eas-cli@latest login`.
- Public HTTPS production API reachable from physical devices and emulators at `/api/v1`.
- Public web build deployed with `VITE_SUPPORT_EMAIL` set to the operator's real support address.
- Dedicated store-review account created; set `STORE_REVIEW_ACCOUNT_EMAIL` and keep the password out of source control.
- EAS environment variables configured with real public values:
  - `EXPO_PUBLIC_API_URL=https://YOUR-DOMAIN/api/v1`
  - `EXPO_PUBLIC_PRIVACY_POLICY_URL=https://YOUR-DOMAIN/privacy`
  - `EXPO_PUBLIC_SUPPORT_URL=https://YOUR-DOMAIN/support`
  - `VITE_SUPPORT_EMAIL=support@YOUR-DOMAIN`
  - `STORE_REVIEW_ACCOUNT_EMAIL=reviewer@YOUR-DOMAIN`
  - `STORE_EXTERNAL_AI_PROCESSING=none` or `self_hosted` or `third_party`
  - `STORE_PRODUCTION_TELEMETRY=none` or `analytics` or `crash_reporting` or `analytics_and_crash_reporting` or `other`
- `mobile/builds/eas-release-evidence.json` created from the example after EAS project, production environment, Android signing, Play app signing, service-account, and submit setup are complete.

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
npx eas-cli@latest build --platform android --profile development
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest build --platform android --profile production
```

For GitHub Actions, add `EXPO_TOKEN` as a repository secret and manually run
`Mobile EAS Build` with `platform=android`. The workflow preflight requires a
real committed EAS project ID, checks repository release artifacts, freezes
existing credentials, queues without waiting, and uploads the JSON build
request. It does not submit the build to Google Play.

After EAS init, production environment setup, and Android signing setup, copy
`mobile/builds/eas-release-evidence.example.json` to
`mobile/builds/eas-release-evidence.json` and record the project ID, production
environment, Android keystore, Play app signing, service account, and submit
setup without adding secret values.

Production output for Google Play should be an Android App Bundle (`.aab`).
After the production build, copy `mobile/builds/native-artifacts.example.json`
to `mobile/builds/native-artifacts.json` and record the Android EAS build ID,
the non-empty `.aab` or `.apk` artifact path under `mobile/builds/`,
`targetSdkVersion`, final `RECORD_AUDIO` permission status, and at least two
tested Android devices.

## Android-Specific Verification

- Confirm the final merged manifest does not include `android.permission.RECORD_AUDIO`.
- Confirm the production artifact targets Android 16 / API 36 or higher before upload.
- Validate Android share intent for `text/*` and `image/*`.
- Validate image picker permission prompt text.
- Exercise offline capture, reconnect sync, search filters, detail edit, export, and account deletion on a physical device.
- Confirm `mobile/builds/native-artifacts.json` records at least two tested devices, the production artifact path under `mobile/builds/`, target API, and permission evidence.

If inspecting a local `.aab`, use Android Studio or `bundletool` to inspect the merged manifest and `targetSdkVersion`.

## Submit

After a production build passes internal testing:

```bash
npx eas-cli@latest submit --platform android --latest
```

For first release, finish Play Console app setup, store listing, content rating, Data safety, account deletion, target audience, and testing-track configuration.

## Sources

- Expo Android production build: https://docs.expo.dev/tutorial/eas/android-production-build/
- Expo CI builds: https://docs.expo.dev/build/building-on-ci/
- Expo EAS build profiles: https://docs.expo.dev/build/eas-json/
- Google Play target API: https://support.google.com/googleplay/android-developer/answer/11926878
