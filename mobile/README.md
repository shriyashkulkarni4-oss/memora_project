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

Native inbound sharing requires a development build; it is not available in
Expo Go. Run `npm run ios` or `npm run android` for inbound sharing. Captures and
search remain functional without a network connection and queued mutations are
retried when connectivity returns.

## Verification

```bash
npm run typecheck
npm run lint
npm test
npm run test:e2e:web
npx expo config --type public
```
