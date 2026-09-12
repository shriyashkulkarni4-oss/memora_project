# Release Checklist

## Build and staging

- [ ] Merge only after all GitHub Actions CI jobs pass.
- [ ] Create a signed `v*` tag and confirm both GHCR images pass Trivy scanning.
- [ ] Deploy immutable image tags to staging with production-like secrets.
- [ ] Run `ops/smoke.sh` and `k6 run ops/k6-smoke.js` against staging.
- [ ] Confirm TLS, secure response headers, throttling, metrics, alerts, worker
      health, screenshot OCR, and link processing.
- [ ] Create and verify a backup; exercise restore in an isolated stack.
- [ ] Confirm the rollback image tags and pre-release backup.

## Web production

- [ ] Confirm DNS, ACME email, privacy-policy URL, operator contact, and backup
      schedule.
- [ ] Deploy, run smoke checks, inspect dashboards, and monitor the first hour.

## Mobile stores

- [ ] Run `eas init` once and commit the generated EAS project ID.
- [ ] Set `EXPO_PUBLIC_API_URL` as an EAS environment secret for preview and
      production.
- [ ] Provide store icons, screenshots, privacy URL, support URL, descriptions,
      content ratings, and data-safety/privacy answers.
- [ ] Configure Apple and Google signing credentials, then run
      `eas build --platform all --profile production`.
- [ ] Test share-sheet capture, offline search, reconnect sync, deep links, photo
      permission, export, and account deletion on physical iOS/Android devices.
- [ ] Submit with `eas submit --platform all --profile production` and use a
      staged rollout.

Store submission and public deployment require organization-owned domain,
hosting, Apple, and Google credentials and therefore are not performed from the
repository development environment.
