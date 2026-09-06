# Mobile Store Readiness

Last checked: 2026-09-06.

## Verdict

The mobile app is not ready for App Store or Google Play production submission yet. Core app functionality is closer after adding mobile export, account deletion, password change, filters, tag editing, privacy/support navigation, and generated store assets, but release identity, signed artifacts, production URLs, real contact details, review access, and store forms are still incomplete.

## Ready

- iOS bundle ID and Android package are set to `com.codingmonkeylabs.memoryhive`.
- EAS build profiles explicitly select matching development, preview, and production environments.
- A manual `Mobile EAS Build` workflow validates the token/project/profile prerequisites, freezes credentials, queues selected production platforms without auto-submission, and uploads the EAS JSON request.
- In-app account deletion is available in Settings.
- Account export is available in Settings.
- Password change forces re-login and clears local mobile data.
- Mobile Settings links to the configured public privacy policy and support URLs.
- Offline capture, local search, and sync logic have unit coverage.
- Android `RECORD_AUDIO` is blocked in app config because the app does not record audio.
- Public web routes exist for `/privacy`, `/account/delete`, and `/support`.
- Public compliance pages read the support mailto address from `VITE_SUPPORT_EMAIL`.
- Frontend release images inject `VITE_SUPPORT_EMAIL` from a GitHub repository variable instead of a placeholder.
- `npm run store:check` reports release blockers from the local mobile config and store-asset handoff directory.
- `npm run store:submission:check` compares expected JSON and Markdown output directly without rewriting files, so missing or stale generated packets fail CI.
- `npm run store:check:ci` fails only for repository-owned readiness defects while continuing to report external release prerequisites.
- `npm run store:check -- --strict` fails for both repository and external release blockers and remains the final submission gate.
- `npm run store:check` tracks the dedicated store-review account email separately from support contact metadata.
- `npm run store:check` treats placeholder or non-public production API, privacy, support, support-email, and reviewer-account values as blockers, while allowing real values from release environment overrides.
- `npm run store:submission -- --release-env-file <path>` and `npm run store:check -- --release-env-file <path>` load release values from an access-controlled env file without editing source-controlled templates.
- `npm run store:check` verifies that `mobile/store-assets/submission-packet.json` matches the same production URLs, support email, reviewer account, and privacy disclosure values being checked.
- `npm run store:check` verifies reviewer passwords remain out-of-band instructions, not committed credentials.
- `npm run store:check` validates store artwork and screenshot PNG dimensions, RGB color type, and generated manifest metadata through unit-tested shared helpers.
- `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` make App Privacy / Data safety disclosure assumptions explicit in the generated packet.
- Store icon source and Google Play feature graphic are generated in `mobile/store-assets/`.
- Store-size iPhone, iPad, Android phone, and Android tablet screenshots are generated in `mobile/store-assets/screenshots/`.
- Store asset and screenshot manifests include release handoff metadata and short alt text.
- `npm run store:submission` generates a structured App Store / Google Play handoff packet.
- `mobile/builds/native-artifacts.example.json` defines the release evidence needed for signed artifacts, multi-device tests, Android target API, and final Android permissions.
- `mobile/builds/eas-release-evidence.example.json` defines the release evidence needed for EAS project identity, production environment variables, signing credentials, and submit setup.
- `mobile/store-assets/store-console-evidence.example.json` defines the evidence needed after App Store Connect, Play Console, and final privacy forms are complete.

## Blocking Gaps

- Run `npx eas-cli@latest init` and commit the generated `extra.eas.projectId`.
- Add a scoped Expo access token as the `EXPO_TOKEN` GitHub Actions secret before using the manual build workflow.
- Create `mobile/builds/eas-release-evidence.json` from the example after EAS production environment, signing credentials, and submit setup are complete.
- Configure public HTTPS production API, privacy policy, and support URLs through EAS or the release environment, using `/api/v1`, `/privacy`, and `/support` paths.
- Create Apple Developer and Google Play app records.
- Configure iOS signing credentials and Android app signing/keystore.
- Produce and record a real iOS `.ipa` artifact under `mobile/builds/` in `mobile/builds/native-artifacts.json`.
- Produce and record a real Android `.aab`/`.apk` artifact under `mobile/builds/` in `mobile/builds/native-artifacts.json`.
- Record at least two native device test records for iOS and Android.
- Verify Android production artifact targets Android 16 / API 36 or higher and does not include `android.permission.RECORD_AUDIO`.
- Deploy `/privacy`, `/account/delete`, and `/support` on the production domain and replace placeholder `VITE_SUPPORT_EMAIL` with a valid support address.
- Set the GitHub repository variable `VITE_SUPPORT_EMAIL` before publishing production frontend images.
- Create a dedicated store-review account, replace placeholder `STORE_REVIEW_ACCOUNT_EMAIL` with a valid reviewer address, and enter its temporary password directly in store consoles.
- Set `STORE_EXTERNAL_AI_PROCESSING` and `STORE_PRODUCTION_TELEMETRY` to match production enrichment, analytics, and crash-reporting behavior before regenerating the packet.
- Complete Google Play short description, full description, category, contact details, content rating, target audience, and Data safety answers.
- Complete Apple app information, screenshots, age rating, App Privacy, review credentials, support URL, and export compliance.
- Create `mobile/store-assets/store-console-evidence.json` from the example after completing store-console fields and privacy verification.
- Replace Expo-web screenshot captures with native-device captures after signed builds if native UI differs or store review requires native screenshots.

## Recommended Order

1. Deploy public privacy, deletion, and support pages on the production domain with `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_PRIVACY_POLICY_URL`, `EXPO_PUBLIC_SUPPORT_URL`, and `VITE_SUPPORT_EMAIL` set to public HTTPS route values and a valid support address.
2. Create a dedicated reviewer account with seeded non-personal data and record only its email in `STORE_REVIEW_ACCOUNT_EMAIL`.
3. Initialize EAS and configure credentials/environment.
4. Produce preview builds and run physical-device tests from the iOS and Android runbooks.
5. Fill `mobile/builds/eas-release-evidence.json` from the example with non-secret project, environment, signing, and submit setup evidence.
6. Fill `mobile/builds/native-artifacts.json` from the example with artifact paths under `mobile/builds/`, multi-device test records, target API, and permission evidence.
7. Review or regenerate store assets with `npm run store:assets` and `npm run store:screenshots`; replace with native captures after signed builds if needed.
8. Run `npm run store:submission -- --release-env-file ../.env.production`.
9. Complete Apple App Privacy, Google Data safety, and store-console forms from `MOBILE_PRIVACY_DATA_SAFETY.md` and `MOBILE_STORE_SUBMISSION_PACKET.md`.
10. Create `mobile/store-assets/store-console-evidence.json` from the example with final form evidence and no reviewer passwords.
11. Run `npm run store:check -- --release-env-file ../.env.production --strict`, then resolve all blockers before submitting.

## Sources

- Apple App Review Guidelines: https://developer.apple.com/app-store/review/guidelines/
- Apple account deletion reminder: https://developer.apple.com/news/?id=12m75xbj
- Apple App Privacy: https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/
- Google account deletion: https://support.google.com/googleplay/android-developer/answer/13327111
- Google Data safety: https://support.google.com/googleplay/android-developer/answer/10787469
- Google target API: https://support.google.com/googleplay/android-developer/answer/11926878
