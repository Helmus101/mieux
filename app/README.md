# Mieux (Expo app)

Native iOS/Android version of Mieux. It reuses `../shared` (API client, zustand stores, i18n, theme, score helpers) unchanged;
only the UI (`src/components/ui.tsx`), navigation (expo-router, `src/app`) and the barcode scanner (`expo-camera`) are native.

```bash
cd app
npm install
npm start            # then press i (iOS simulator), a (Android) or scan the QR code with Expo Go
```

## Backend URL

The app talks to the same FastAPI backend as the web app, which listens on port **8010**. The app finds it by itself: it uses the
computer running `npm start` (so a real phone on the same Wi-Fi works with no setting), falling back to `localhost:8010` in a simulator.
The default `scripts/run.sh` binds to 127.0.0.1 only, which a phone cannot reach; start the API for the phone with:

```bash
scripts/run-lan.sh          # same API, listening on 0.0.0.0:8010
```

To point at another server (a deployed one): `EXPO_PUBLIC_API_URL=https://example.com/v1 npm start`.

## Screens

| Route | Web equivalent |
|---|---|
| `/onboarding` | Onboarding |
| `/(tabs)/scan` | Scan (live camera, torch, barcode from a photo) |
| `/(tabs)/list` | Saved list, links to compare and history |
| `/(tabs)/profile` | Profile (name, home address, language, diet, allergens, stores, export, erase) |
| `/product/[barcode]` | Product (scores, flags, breakdown, nutrition, additives, where to buy, ingredients) |
| `/alternatives/[barcode]` | Alternatives (budget/balanced/nutrition, store filter) |
| `/compare`, `/history` | Compare, History |

Not ported: landing page, blog, usage stats (see `../docs/EXPO.md`).

## Notes

- Storage: `src/lib/boot.ts` preloads AsyncStorage into the synchronous adapter the shared stores expect, then hydrates them.
- `shared/config.ts` no longer reads `import.meta` (Hermes cannot parse it); the web app sets its base URL in `web/src/main.tsx`.
- `npm run typecheck` runs `tsc`; `npx expo export --platform ios` verifies the bundle.
