# Mobile Store Assets

This directory is the handoff location for App Store and Google Play artwork.

Generated assets:

- `icon-1024.png`: 1024x1024 RGB PNG app icon source.
- `feature-graphic.png`: 1024x500 RGB PNG Google Play feature graphic.
- `manifest.json`: generated asset inventory with dimensions, purpose, and alt text.
- `submission-packet.json`: generated App Store / Google Play handoff packet.
- `store-console-evidence.example.json`: template for final App Store Connect,
  Play Console, and privacy-form completion evidence.

Run `npm run store:assets` from `cml-memoryhive-mobile/` to regenerate these files.

Screenshot capture:

- `screenshots/`: iPhone, iPad, Android phone, and Android tablet screenshots plus a manifest with platform, form-factor, dimensions, screen, and alt text.

Run `npm run store:screenshots` with a local backend running to refresh screenshots.
Use native device screenshots for final App Store and Google Play submission if store review requires device-native captures.
`npm run store:check` validates expected PNG dimensions, RGB color type, and
manifest metadata through `cml-memoryhive-mobile/scripts/store-asset-readiness.mjs`.

After App Store Connect and Play Console fields are complete, copy
`store-console-evidence.example.json` to `store-console-evidence.json`, fill in
the final form evidence, and keep reviewer passwords out of both files.

Run `npm run store:submission` to refresh `submission-packet.json` and `docs/GOAL-1/MOBILE_STORE_SUBMISSION_PACKET.md`.
Run `npm run store:submission:check` with the same environment to verify both
generated files without modifying them. CI uses this command so deleted,
missing, or stale packet outputs fail before the broader readiness check.
Provide real release values through the environment when generating the final
packet: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRIVACY_POLICY_URL`,
`EXPO_PUBLIC_SUPPORT_URL`, `VITE_SUPPORT_EMAIL`, and
`STORE_REVIEW_ACCOUNT_EMAIL`, plus `STORE_EXTERNAL_AI_PROCESSING` and
`STORE_PRODUCTION_TELEMETRY`. URLs must be public HTTPS values for `/api/v1`,
`/privacy`, and `/support`; emails must be valid non-placeholder addresses.
Disclosure fields must match production enrichment and telemetry behavior. Run
`npm run store:check` with the same environment; readiness fails when the packet
does not match those values.

```bash
npm run store:submission -- --release-env-file ../.env.production
npm run store:check -- --release-env-file ../.env.production --strict
```

Record signed native build evidence in `../builds/native-artifacts.json` using
`../builds/native-artifacts.example.json` after EAS production builds finish.
Run `npm run store:check` to see current gaps. Add `-- --strict` when using it as a release gate.
