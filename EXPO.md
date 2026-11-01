# Moving Mieux to Expo (React Native)

The web app is built so only a thin layer changes.

| Layer | Web today | Expo |
|---|---|---|
| Business logic, API client, stores, i18n, theme tokens, format helpers (`shared/`) | platform-free TypeScript (zustand, axios) | **reuse as is**; call `setStorage(AsyncStorage)` once at startup (`shared/storage.ts`) |
| UI primitives (`web/src/ui/index.tsx`) | DOM + CSS | re-implement this one file with `View/Text/Pressable`, `Animated`/Reanimated (CountUp, Bar), `@gorhom/bottom-sheet` (Sheet), `expo-haptics` (haptic), `expo-blur` (tab bar/nav bar) |
| Navigation (`web/src/nav.ts`, `App.tsx`) | react-router | expo-router or React Navigation; same route names |
| Barcode (`screens/Scan.tsx`) | getUserMedia + ZXing | `expo-camera` `CameraView onBarcodeScanned` |
| Receipt OCR (`ReceiptCapture.tsx`) | tesseract.js | Apple Vision / ML Kit (on device), send line text to `/v1/receipts/preview` |
| Screens (`web/src/screens/*`) | import only from `../ui`, `@shared/*`, `../nav` | copy over; swap `<table>`/`<input>`/`<img>` for RN equivalents |
| Colors/spacing/type | CSS variables mirroring `shared/theme.ts` | import `shared/theme.ts` into `StyleSheet` |

Data stays on the device: the backend runs on 127.0.0.1 (SQLite). For a standalone phone app, port the small backend modules (engine, receipts, value) to TypeScript or ship them behind a local server; only barcodes ever leave the device (Open Food Facts / Open Prices).
