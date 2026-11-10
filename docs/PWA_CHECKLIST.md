# Mieux as an installed phone app (PWA): what is in place and what to check before each release

The web app at `/app` is the product on iPhone and Android. This is the list of what makes it behave like an installed app and stay healthy in production.

## In place

| Concern | Where | What it does |
|---|---|---|
| Install | `web/public/manifest.webmanifest` | `id`, 192/512 icons (`any` + separate `maskable`), shortcuts (Scanner, Enregistrés, Comparer), standalone display, portrait |
| Instant open | `web/public/sw.js` | Shell cached; fresh copy when the network answers within 1.2 s, cached copy otherwise; hashed assets cache-first; API never cached |
| First visit offline | `web/public/sw.js` | A small inline "hors ligne" page instead of the browser error |
| New version | `web/src/sw-client.ts`, `UpdateToast.tsx` | Checks for a new build when the app returns to the foreground; "Nouvelle version disponible · Actualiser" toast when one has taken over |
| Stale script after a deploy | `web/src/ErrorBoundary.tsx` | One automatic reload, then a visible error with a reload button |
| Offline while using | `web/src/NetStatus.tsx` | Thin bar while offline, toast when back; product sheets already opened come from the device history |
| Errors in production | `web/src/report.ts` → `POST /v1/client-errors` | Uncaught errors and render failures logged server-side (`grep client_error`), with the build version; max 5 per page load, no personal data |
| Build version | `vite.config.ts` (`__APP_VERSION__`) | `package.json` version + git commit, shown at the bottom of Profil |
| Native feel | `web/src/gestures.ts`, `App.tsx`, `index.css` | Edge-swipe back in the installed app, haptics, tab re-tap scrolls to top, new screens start at the top, safe-area padding, no rubber-band, 44 px targets, reduced-motion respected |
| Fast alternatives | `web/src/alternatives.ts` | The product page starts the exact alternatives request the next screen will make; the screen joins the in-flight request or reads the cached answer |
| Loading | skeletons in `Product.tsx` / `Alternatives.tsx` | The screen's own shape in placeholders plus one step line; no spinner |
| Headers | `vercel.json` | CSP, HSTS, no-store on `sw.js`, immutable `/assets`, correct manifest content type |

## Before each release

1. `cd web && npx tsc --noEmit && npx vitest run && npm run build` (CI does the same).
2. `cd backend && python -m pytest`.
3. Changed `sw.js`? Bump the cache name (`mieux-shell-vN`).
4. On a phone, from the deployed URL: install from the browser menu, open from the home screen, scan one product, open the alternatives, switch to airplane mode and reopen a product already seen.
5. After deploying, keep the previous tab open and confirm the update toast appears when it returns to the foreground.
6. `fly logs | grep client_error` for the first hour.

## Not done (deliberately)

- iOS splash images (`apple-touch-startup-image`): about 20 PNGs for current devices; the white boot screen with the logo (`index.html` `#boot`) covers the gap.
- Push notifications: no use case yet.
- A third-party error tracker: the server log line is enough at the current scale.
