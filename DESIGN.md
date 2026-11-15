# Design

Derived from `web/src/index.css`, `web/src/landing.css` and `shared/theme.ts`. Update those first; this file follows.

## Character
Quiet, Apple-adjacent utility: neutral surfaces, one deep green accent, large tightly tracked headlines, pill actions, almost no shadow in the app. Landing adds one lifted "product shot" card.

## Color
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | #FFFFFF | #0D1210 | page |
| `--card` / `--bg2` | #F5F5F7 | #151C18 | cards, alternate bands |
| `--ink` | #14201A (app) / #1D1D1F (landing) | #F2F5F3 | text |
| `--mut` / `--soft` | #5A6660 / #636366 | #A3AFA8 | secondary text |
| `--leaf` / `--accent` | #1F4D3A | #6FCF97 | primary action, links, kickers |
| `--olive` | #7FA65A | #9CBE77 | good-ish tone |
| `--clay` | #F26B3A | #FF8A5C | caution tone |
| `--warn` | #D95A22 | #FF9A6B | low score |
| `--bad` | #A33B2B | #E4695A | harmful / error |
| `--line` | rgba(60,60,67,.16) | #24302A | hairlines |

Score tones: g, g2, y, w, b map to accent, olive, clay, warn, bad. Dark mode follows `prefers-color-scheme`.

## Typography
System stack (SF Pro / Segoe / Roboto), tabular numerals. Landing H1 `clamp(40px, 8.4vw, 88px)`, weight 700, tracking -.045em; H2 `clamp(30px, 5.4vw, 56px)`; body 17px; small print 12-13px. App h2 16px/600, h3 17px/600.

## Shape and space
Radius 8 / 12 (app), 14-28 (landing cards), pills 999px for buttons. Landing page gutter `max(clamp(20px,5vw,40px), (100% - 1040px)/2)`; sections 64-128px vertical.

## Components
- Primary button: leaf fill, pill, min height 44px (32px in the nav bar), press scale .97.
- Card: `--card` fill, no border, no shadow in the app.
- Score badge: warn/tone fill, white number, `/100` suffix.
- Price figure: bold per-kilo price plus a pill diff (green down, grey up).
- Inputs: tinted fill, 12px radius, 3px tint focus ring; focus-visible 2px outline.

## Motion
Hero entrance only (12px rise, .5s, ease `cubic-bezier(.32,.72,0,1)`); landing sections fade in on scroll. Nothing loops. All motion off under `prefers-reduced-motion`; blur off under `prefers-reduced-transparency`.

## Rules
- One dominant action per view.
- No decorative imagery; product photos and the real example carry the page.
- Keep landing and app tokens in sync with `shared/theme.ts`.
