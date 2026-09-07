# Mobile Native Build Evidence

This directory is the local handoff area for release build evidence.

Do not commit `.ipa`, `.aab`, or `.apk` files. They are ignored because signed
native artifacts are large release outputs and may contain account-specific
signing metadata.

The manual `Mobile EAS Build` GitHub workflow queues production builds after
its token, project, profile, submission-packet, and repository-readiness gates
pass. It uploads the ignored `eas-build-request.json` as a 30-day workflow
artifact. Use its build IDs and links to monitor EAS, then download completed
native artifacts for the evidence process below. The workflow freezes existing
credentials and deliberately does not auto-submit.

When production artifacts exist, copy
`native-artifacts.example.json` to `native-artifacts.json` and fill in:

- EAS build IDs and production profile names.
- Real, non-placeholder EAS build IDs.
- Local non-empty artifact paths under `cml-memoryhive-mobile/builds/` with the correct
  platform extension: `.ipa` for iOS and `.aab` or `.apk` for Android.
- At least two tested device names and OS versions per platform.
- Android `targetSdkVersion`.
- Whether `android.permission.RECORD_AUDIO` appears in the final merged
  Android manifest.

When EAS setup is complete, copy `eas-release-evidence.example.json` to
`eas-release-evidence.json` and record non-secret evidence for:

- EAS project ID matching `cml-memoryhive-mobile/app.json`.
- Production EAS environment configured with public mobile URLs.
- iOS credentials, Apple team ID, production profile, and submit setup.
- Android keystore, Play app signing, service account, and submit setup.

Run `npm run store:check` from `cml-memoryhive-mobile/` after updating the manifest.
