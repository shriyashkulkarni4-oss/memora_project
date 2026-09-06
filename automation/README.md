# Memoryhive Automation

This package orchestrates Goal 1 integration checks from the repository root. It
reuses the canonical seed script, Docker lifecycle wrapper, smoke test, and the
existing web/mobile Playwright suites.

## Commands

```bash
npm --prefix automation run doctor
npm --prefix automation run seed -- --persona engineer
npm --prefix automation run validate
npm --prefix automation run test
npm --prefix automation run test:docker
npm --prefix automation run test:docker:cleanup
```

`test` expects the backend to be reachable at `BASE_URL` or
`http://localhost:8000`. `test:docker` starts the Compose dev stack first,
runs migrations, and clears transient Redis `rate:*` keys so repeated auth-heavy
test runs do not need a volume reset. Add `--temporal` to run against the
Temporal Compose profile.

## Options

- `--base-url URL`: backend origin, for example `http://localhost:8000`.
- `--persona engineer|student|commerce|home|all`: demo data to seed.
- `--skip-web` or `--skip-mobile`: skip one Playwright surface.
- `--cleanup`: stop Compose services after the run.
- `--clean-volumes`: call `ops/dev-stack.sh clean`; requires
  `CONFIRM_CLEAN=memoryhive`.
- `--dry-run`: print the command plan without executing it.

The runner deliberately does not duplicate browser scenarios. Keep workflow
assertions in `frontend/e2e/` and `mobile/e2e/`, then use this package for
repeatable local or CI orchestration.
