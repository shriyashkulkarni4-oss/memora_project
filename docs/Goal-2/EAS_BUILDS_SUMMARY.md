# Memoryhive EAS Build Summary

Last verified: 2026-09-08 23:12 IST

## Current Status

Memoryhive is linked to Expo Application Services (EAS), and the mobile
configuration resolves successfully. No completed native artifact has been
produced yet.

| Item | Value |
| --- | --- |
| EAS project | `@codingmonkeylabsadmins-team/memoryhive` |
| EAS project ID | `7fae7de6-5aad-4bdd-85fe-ff59e1e21b9a` |
| Expo SDK | 54 |
| App version | `1.0.0` |
| iOS bundle ID | `com.codingmonkeylabs.memoryhive` |
| iOS share extension | `com.codingmonkeylabs.memoryhive.share-extension` |
| Android package | `com.codingmonkeylabs.memoryhive` |
| Version source | EAS remote versioning |
| Current remote iOS build number | `5` |
| Current remote Android version code | `3` |
| EAS Update channel | `production` |

The static `ios.buildNumber` and `android.versionCode` values in `app.json`
are retained in the application manifest, but EAS ignores them for build
numbering because `cli.appVersionSource` is `remote`.

## Live Build

One Android production build is currently queued:

| Item | Value |
| --- | --- |
| Build ID | `18869d8a-b4ae-4a48-924d-e43cd9aaa012` |
| Platform | Android |
| Status at last verification | `IN_QUEUE` |
| Profile | `production` |
| Distribution | Store |
| Channel | `production` |
| Version/version code | `1.0.0` / `3` |
| Artifact | Not available while queued |
| Source commit | `a111b7f30274066cb9f5fa906f5137585b67d248` |
| Build logs | <https://expo.dev/accounts/codingmonkeylabsadmins-team/projects/memoryhive/builds/18869d8a-b4ae-4a48-924d-e43cd9aaa012> |

Check its latest state with:

```bash
cd cml-memoryhive-mobile
npx eas-cli@latest build:view 18869d8a-b4ae-4a48-924d-e43cd9aaa012
```

## Repository Tooling

The repository currently provides:

- EAS `development`, `preview`, and `production` profiles in
  `cml-memoryhive-mobile/eas.json`.
- EAS project identity, Update URL, and runtime policy in
  `cml-memoryhive-mobile/app.json`.
- `expo-updates` for the configured preview and production channels.
- Mobile EAS preflight and store-readiness checks.
- A manually dispatched GitHub Actions workflow at
  `.github/workflows/mobile-eas-build.yml` for production iOS, Android, or
  combined builds.

The GitHub workflow is intended for repeatable production builds after initial
credentials exist. It requires an `EXPO_TOKEN` GitHub Actions secret and uses
`--freeze-credentials`, so it cannot create first-time credentials.

## Build Profiles

| Profile | Distribution | Environment | Intended use |
| --- | --- | --- | --- |
| `development` | Internal development client | `development` | Native development with a Metro server |
| `preview` | Internal | `preview` | Direct testing before store release |
| `production` | Store | `production` | App Store or Google Play artifacts |

`expo-dev-client` is not currently installed. The existing `development`
profile can build without it, but installing it provides the normal Expo
development-client launcher and debugging workflow:

```bash
cd cml-memoryhive-mobile
npx expo install expo-dev-client
```

## Attempts and Resolutions

### EAS project initialization

`npx eas-cli@latest init` created and linked the EAS project successfully, then
failed while re-evaluating the Expo configuration. The `expo-share-intent`
plugin output had been written back into static `app.json`, creating duplicate
`ShareExtension` entries and generated Android permission entries.

The generated duplicates were removed while preserving the new EAS project ID.
Expo configuration and Expo Doctor subsequently passed.

### First iOS production attempt

The first attempt installed and configured `expo-updates`, added the Update URL
and runtime policy, and requested that the command be rerun. That configuration
step again persisted generated `expo-share-intent` output into `app.json`; the
generated fields were removed while retaining the legitimate EAS Update setup.

The next attempt reached Apple credential configuration for both the main app
and `ShareExtension`. It was stopped because no Apple Developer Program account
is currently available. No iOS build was queued and no `.ipa` exists.

### Android production attempt

The initial Android attempt stopped before upload because Git tracked
`docs/Presentations` while the macOS filesystem exposed the directory as
`docs/presentations`. EAS temporarily enables Git case sensitivity and reported
the entire presentation tree as inconsistent.

The directory was corrected to the exact tracked casing, preserving its tracked
and untracked contents. The EAS casing check, Android profile resolution, Expo
Doctor, and all 61 mobile tests then passed. A subsequent Android production
request created the queued build recorded above.

## Testing Without Store Developer Accounts

Google Play and Apple Developer memberships are not required for the following
test paths:

| Platform | Supported path | Output/account constraint |
| --- | --- | --- |
| Android device or emulator | EAS internal `preview` build | Installable APK; no Play account required |
| iOS Simulator | EAS simulator build | No Apple Developer account required |
| Web | Expo web build | Browser testing; no native account required |
| Physical iPhone/iPad through EAS | Not currently available | Requires Apple signing and Developer Program access |
| TestFlight | Not currently available | Requires Apple Developer Program and App Store Connect |

Build an installable Android test APK with the existing profile:

```bash
cd cml-memoryhive-mobile
npx eas-cli@latest build --platform android --profile preview
```

If EAS asks for an Android keystore, allow EAS to generate and manage it. A
Google Play account is needed for Play Store submission, not for generating an
APK or Android App Bundle.

The repository does not yet contain an iOS Simulator profile. Add a dedicated
profile before requesting an unsigned simulator build:

```json
{
  "build": {
    "ios-simulator": {
      "extends": "preview",
      "ios": {
        "simulator": true
      }
    }
  }
}
```

Then build and install it with:

```bash
cd cml-memoryhive-mobile
npx eas-cli@latest build --platform ios --profile ios-simulator
npx eas-cli@latest build:run --platform ios --latest
```

Running the downloaded iOS build locally requires full Xcode and the iOS
Simulator. Store membership is not required for a simulator artifact.

## Environment Configuration

At the last verification, EAS reported no plain-text or sensitive variables in
the `development`, `preview`, or `production` environments. Native builds can
compile without them, but a physical device will not reach a useful backend
using the app's localhost fallback.

Configure these variables for the target EAS environment:

```text
EXPO_PUBLIC_API_URL=https://YOUR-TEST-DOMAIN/api/v1
EXPO_PUBLIC_PRIVACY_POLICY_URL=https://YOUR-TEST-DOMAIN/privacy
EXPO_PUBLIC_SUPPORT_URL=https://YOUR-TEST-DOMAIN/support
```

For shared Android-device and iOS-Simulator testing, use a reachable public
HTTPS test deployment. Do not use `localhost` for a physical Android device.

## Validation Commands

Run these from `cml-memoryhive-mobile` before requesting another build:

```bash
npm ci
npm run typecheck
npm run lint
npm test
npx expo-doctor
npx eas-cli@latest project:info
npx eas-cli@latest config --platform android --profile preview
```

Current verified results:

- Expo Doctor: 18/18 checks passed.
- Mobile tests: 61 passed.
- Expo configuration: resolves successfully.
- EAS Android preview profile: resolves successfully.
- Git filename-casing audit: passes.

## Remaining Release Requirements

These items are not required for Android APK or iOS Simulator testing, but they
are required before store release:

- Apple Developer Program membership, App Store Connect application, and iOS
  signing credentials for the app and share extension.
- Google Play Developer account, Play Console application, Play App Signing,
  and service-account submission access.
- Real production API, privacy-policy, and support URLs configured in EAS.
- A real support address and dedicated store-review account.
- `EXPO_TOKEN` configured for the GitHub Actions production-build workflow.
- Completed signing, device-test, artifact, and store-console evidence files
  described by the mobile release-readiness tooling.

## References

- Expo EAS Build setup: <https://docs.expo.dev/build/setup/>
- Android APK builds: <https://docs.expo.dev/build-reference/apk/>
- iOS Simulator builds: <https://docs.expo.dev/build-reference/simulators/>
- EAS environment variables: <https://docs.expo.dev/eas/environment-variables/>
