# Memoryhive Mobile

Offline-first Expo client for the canonical Memoryhive `/api/v1` service.

## Local development

```bash
npm ci
EXPO_PUBLIC_API_URL=http://YOUR-LAN-IP:8000/api/v1 npm start
```

Native inbound sharing requires a development build; it is not available in
Expo Go. Run `npm run ios` or `npm run android` after setting a reachable API
URL. Captures and search remain functional without a network connection and
queued mutations are retried when connectivity returns.

## Verification

```bash
npm run typecheck
npm run lint
npm test
npx expo config --type public
```
