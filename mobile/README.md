# Memoryhive Mobile

Offline-first Expo client for the canonical Memoryhive `/api/v1` service.

## Local development

```bash
npm ci
npm start
```

The development client derives the backend host from the browser hostname or
Expo host URI, with `10.0.2.2` as the Android emulator fallback. Use
`EXPO_PUBLIC_API_URL=http://YOUR-HOST:8000/api/v1 npm start` when the backend is
served from a different machine or port.
Set `EXPO_PUBLIC_PRIVACY_POLICY_URL` and `EXPO_PUBLIC_SUPPORT_URL` for release
builds; otherwise the app derives `/privacy` and `/support` from the configured
API origin.
For store review, set `STORE_REVIEW_ACCOUNT_EMAIL` to a dedicated reviewer
account and keep its temporary password outside source control.
`npm run store:submission` and `npm run store:check` also honor environment
overrides for `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRIVACY_POLICY_URL`,
`EXPO_PUBLIC_SUPPORT_URL`, `VITE_SUPPORT_EMAIL`, and
`STORE_REVIEW_ACCOUNT_EMAIL`. Readiness requires public HTTPS `/api/v1`,
`/privacy`, and `/support` routes plus valid non-placeholder email addresses.
Set `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` so the
generated privacy/data-safety draft matches production enrichment and telemetry.
Run both commands with the same release environment so the generated packet
matches the checked config.
`npm run store:submission:check` verifies both generated output files byte for
byte without rewriting them and fails when either file is missing or stale.
`npm run store:check:ci` fails for repository-owned readiness defects but keeps
missing account credentials, signed builds, and store-console evidence visible
as release blockers. Final submission still requires `store:check -- --strict`.

```bash
npm run store:submission -- --release-env-file ../.env.production
npm run store:check -- --release-env-file ../.env.production --strict
```

After EAS production builds finish, record signed artifact paths, tested
devices, Android `targetSdkVersion`, and merged-manifest permission evidence in
`builds/native-artifacts.json` from `builds/native-artifacts.example.json`.
Artifact paths must point to non-empty platform files under `mobile/builds/`,
and each platform needs at least two tested device records.
After EAS project, production environment, and signing setup are complete,
record non-secret setup evidence in `builds/eas-release-evidence.json` from
`builds/eas-release-evidence.example.json`.
After App Store Connect, Play Console, and privacy forms are complete, copy
`store-assets/store-console-evidence.example.json` to
`store-assets/store-console-evidence.json` and record final form evidence
without reviewer passwords.

For remote production builds, first authenticate EAS, run the initial
interactive platform builds, commit `expo.extra.eas.projectId`, and add an
`EXPO_TOKEN` GitHub Actions secret. The manual `Mobile EAS Build` workflow runs
`eas:build:preflight`, queues `ios`, `android`, or `all` with frozen credentials,
does not submit to a store, and uploads `eas-build-request.json` as a workflow
artifact. The three EAS profiles explicitly select their matching development,
preview, and production environments.

Native inbound sharing requires a development build; it is not available in
Expo Go. Run `npm run ios` or `npm run android` for inbound sharing. Captures and
search remain functional without a network connection and queued mutations are
retried when connectivity returns.

Settings includes account export, password change, sign out, privacy policy,
support, and permanent account deletion. Export and deletion require a network
connection because they use the canonical backend account endpoints.

## Verification

```bash
npm run typecheck
npm run lint
npm test
npm run test:e2e:web
npm run eas:build:preflight
npm run store:assets
npm run store:screenshots
npm run store:submission
npm run store:submission:check
npm run store:check
npm run store:check:ci
npx expo config --type public
```
