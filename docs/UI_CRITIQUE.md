# UI critique and production readiness (2026-11-23)

Evidence: Playwright screenshots of the built web app against a local backend (mobile 390x844 iPhone UA, desktop 1280x800), DOM checks
per page (horizontal scroll, touch target size, unlabeled buttons, images without alt), live header and CORS checks, `npm audit`,
git-history secret scan. The network dropped during the first run, so only screens that rendered cleanly are judged below.

## UI findings

Seen and good: onboarding (one headline, three points, one action), product page (Qualité / Valeur in one card, numerals in tone
colour), alternatives cards with the new styles (photo, Valeur badge, price per kilo and difference, store chips), profile layout.
No horizontal scroll, no unlabeled buttons and no images without alt on the pages checked.

| Priority | Screen | Finding | Status |
|---|---|---|---|
| P1 | Alternatives | The quality figure was a bare star and number ("★ 97"); DESIGN.md requires Qualité to be labelled | Fixed: now "Qualité 97" |
| P1 | Alternatives | "Voir plus d'alternatives" was plain grey left-aligned text with no button affordance | Fixed: secondary button |
| P2 | Alternatives | Store chip row is cut hard at the right edge ("Monopri"); a fade would show it scrolls | Open |
| P2 | Alternatives | Cards in a row have different heights when a name wraps, so price rows do not line up | Open |
| P2 | Alternatives | Product photos are cropped tightly on mobile (some show only part of the pack) | Open |
| P2 | Product | The "Mauvaise catégorie ?" link sits between the score note and the first card and reads as a stray line | Open: move into the disclosure group |
| P2 | Profile | 9 interactive elements under 40 px (chips and rows) on both widths | Open: audit against the 44 px rule |
| P2 | Accessibility | Few `aria-` / `role=` attributes in Compare, Onboarding, Profile, History, Legal, Blog | Open: run axe per screen |
| P2 | Landing / app | `/_vercel/insights/script.js` 404s only on localhost (expected) | None |

Not done: Lighthouse and axe runs, keyboard and screen-reader pass, dark mode (the app is light only by design), the camera
scanner on a real device, the Expo app.

## Production readiness

| Check | Result | Evidence |
|---|---|---|
| Secrets in repo | Pass | `backend/.env` ignored; no `sb_secret_`, `sb_publishable_` or JWT-shaped keys in any commit |
| Web security headers | Pass | CSP, HSTS, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy on Vercel |
| API security headers | Pass | HSTS, X-Frame-Options, nosniff on Fly |
| CORS | Pass | Preflight from an unlisted origin is refused (400) |
| API health | Pass | `/health/ready` ready, about 45 ms warm |
| CI | Pass | pytest + alembic check + web tsc / vitest / build; backend deploys on push to `main` |
| Tests | Pass | 772 backend, 20 web |
| Dependencies | Risk | `react-router` / `react-router-dom` 6.30.6 moderate advisory (open redirect via backslash in `<Link>` / `useNavigate`); fix needs v7 (breaking) |
| Error monitoring | Fail | None configured |
| Uptime alerting | Fail | None configured |
| Database backups | Unverified | Fly volume snapshots not checked; index rollback copies exist (`alt_index.db.prev-*`) |
| Redundancy | Accepted risk | One Fly machine (owner decision); each deploy restarts it |
| Supabase "Get started" counter | Unverified | `onboarding_total` SQL must be run once in the Supabase editor |
| Migration `c7e2a9b4d1f0` in prod | Likely pass | Tables are created on start (`create_all`); the live flag endpoint answered 200 |
| Lighthouse / Core Web Vitals | Not run | |
| Accessibility audit (axe) | Not run | |
| Classification accuracy | Info | 79% type level on a 153-row self-labelled sample (`backend/tests/data/taxonomy_hand_check.csv`) |

## Next
1. Add error reporting and an uptime check.
2. Run Lighthouse and axe on the main screens and fix what they flag.
3. Fix the open P2 items above.
4. Verify Fly volume snapshots and the Supabase SQL.
5. Plan the `react-router` v7 upgrade.
