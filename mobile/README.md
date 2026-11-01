# FoodIQ mobile (Expo / React Native)

Reuses `../shared` unchanged (API client, stores, French translations, theme, additives, barcode check). Only the UI layer is React Native:
`src/ui.tsx` (same primitives as `web/src/ui`), `src/nav.ts` (expo-router), `src/storage.ts` (AsyncStorage preloaded into the sync adapter), `src/ocr.ts`.

## Run
```bash
cd mobile && npm install --legacy-peer-deps
EXPO_PUBLIC_API_URL=http://<your-computer-LAN-IP>:8010/v1 npx expo start     # scan the QR code with Expo Go
```
- Simulator on the same machine: the default `http://localhost:8010/v1` works (Android emulator uses `10.0.2.2` automatically).
- A physical phone needs the backend reachable on your network: `cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010`
  (this exposes your local API to your Wi-Fi; switch back to `127.0.0.1` afterwards).

## Checks
`npm run typecheck` · `npm run bundle:check` (web) · `npx expo export --platform ios --platform android` (native bundles).

## Not done
- **Receipt OCR on device**: `src/ocr.ts` returns "not available" in Expo Go; the screen falls back to pasting text. Needs a development build + ML Kit / Apple Vision.
- No device/simulator run has been performed here, only type-check and Metro bundling for web, iOS and Android.
- The "History" screen, a native Sheet gesture and haptics tuning are web-only or basic.
