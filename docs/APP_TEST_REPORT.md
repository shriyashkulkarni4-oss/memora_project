# Application Integration Test Report

Last verified: 2026-09-06

## Runtime architecture

The local Docker Compose stack runs PostgreSQL, MinIO, Redis, FastAPI, the
processing worker, and the React/Vite web application. The native Expo client
runs on the host or a phone/emulator by design; it connects to the Compose
backend through host port `8000`.

Local entry points:

- Web application: `http://localhost:3000`
- Backend API: `http://localhost:8000/api/v1`
- API documentation: `http://localhost:8000/docs`
- Expo web: `http://localhost:8083`
- MinIO console: `http://localhost:9001`

The root `automation/` package orchestrates repeatable Goal 1 integration runs
by seeding data, running `ops/smoke.sh`, and invoking the web and mobile
Playwright suites against a configured backend.

## Issues found before fixes

| Issue | Impact | Resolution |
| --- | --- | --- |
| Expo origin `http://localhost:8083` failed CORS preflight | Mobile web login and all API calls failed | Development CORS now accepts localhost and private-network origins on any port; public origins remain denied |
| Mobile API URL was hardcoded to `localhost` | Phones and Android emulators called themselves instead of the backend | The client now derives the web/Expo host, uses `10.0.2.2` as the Android fallback, and honors `EXPO_PUBLIC_API_URL` overrides |
| Development trusted-host validation rejected LAN IPs and Docker service hosts | Physical clients and the Vite container proxy received HTTP 400 | Development accepts dynamic host headers; production still rejects wildcard host configuration |
| The Compose Vite proxy targeted its own container | Same-origin `/api` calls failed with connection refused | Compose uses `/api/v1` and proxies internally to `http://backend:8000` |
| Asset downloads redirected to `http://minio:9000` | Screenshot previews failed because browsers cannot resolve Docker DNS | Authenticated asset bytes are streamed through the backend with private caching |
| Mobile API routing had no integration coverage | CORS and device-host regressions were not detected | Added API URL unit tests and a real Expo-web Playwright workflow |
| React Native Web warned for legacy `shadow*` style properties | Mobile web test output hid useful runtime diagnostics in repeated deprecation warnings | Shared shadows now use CSS `boxShadow` on web and retain native shadow/elevation properties on iOS and Android |

## Expected use cases and results

| Area | Use case | Result |
| --- | --- | --- |
| Authentication | Register, sign in, restore/refresh a session, sign out | Pass |
| Demo access | Sign in as a seeded user from web and mobile | Pass |
| Capture | Save links, text notes, and screenshots | Pass |
| Local first | Save locally, push queued changes, pull server changes | Pass |
| Search | Search title, text, URL, and tags; retain results after reload | Pass |
| Organization | Create categories, tag items, favorite, archive, and restore | Pass |
| Editing | Edit an item with revision handling | Pass |
| Failure handling | Roll back a failed optimistic favorite update | Pass |
| Private assets | Upload and render an authenticated screenshot preview | Pass |
| Lifecycle | Delete an item, export account data, and delete an account | Pass |
| Responsive UI | Desktop web at 1440x900 and mobile at 390x844 | Pass |
| Native bundles | Export iOS, Android, and web bundles | Pass |
| Automation | Seed, smoke, web Playwright, mobile Playwright, and optional Compose cleanup | Pass |

## Verification evidence

- Full automation runner: `npm --prefix automation run test:docker:cleanup` rebuilt Compose, validated services, seeded all personas, passed API smoke, passed both Playwright suites, and stopped the stack while preserving volumes.
- Backend: `35 passed`; Ruff and Black clean.
- Frontend: production build passed; `17` Vitest tests passed.
- Frontend live Playwright workflow: `1 passed` against the real API.
- Mobile: TypeScript and Expo lint clean; `61` Vitest tests passed.
- Mobile Expo-web Playwright workflow: `1 passed` against the real API.
- Expo export produced iOS, Android, and web bundles successfully.
- Compose services reported healthy after rebuild.
- CORS preflights passed for `localhost:8083` and a LAN origin; an unrelated
  public origin remained blocked.

## Remaining release checks

- Run the generated native app on at least one physical iOS device and one
  physical Android device to validate OS share-sheet integration and real LAN
  connectivity.
- Third-party link extraction can fail for URLs that reject automated requests
  or return errors. Captures remain stored and processing can be retried.
