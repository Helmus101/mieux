# Implementation brief — simplify Mieux web UX

> Audience: implementing agent (Claude or other). Scope: `web/` (React + Vite + TS). Backend changes only if strictly needed; see §7.
> Status of audit: static source/CSS review only — nothing has been verified in a rendered browser. Re-verify assumptions against current `main` before editing.

## 0. Goal

One objective for the whole product: **scan a product → understand whether it is good → find a better alternative → understand its value.** Everything else is secondary.

The problem is information density, not visual identity. Keep the green/white/restraint direction; remove competing scores, repeated explanations, and secondary actions.

Design direction (apply everywhere):

- White background, dark-ink text, forest-green primary actions, muted-grey secondary text, very light grey dividers.
- Thin separators instead of containers; cards only for important warnings/exceptional info.
- Flat rows for almost everything; one primary piece of information per component.
- Consistent border radius (restrained, e.g. 12–16px), one spacing scale, 44px minimum touch targets.
- Colour only when it communicates something meaningful (score tones, warnings, price deltas).
- Progressive disclosure: show what the current decision needs; collapse the rest.

## 1. File map (verified)

| Area | Files |
|---|---|
| Product screen | `web/src/screens/Product.tsx` |
| Alternatives screen | `web/src/screens/Alternatives.tsx` |
| Scanner | `web/src/screens/Scan.tsx`, `web/src/ScanPeek.tsx`, `web/src/scanner.ts` |
| Saved/List | `web/src/screens/List.tsx` (route name "Saved"/"List" — check `nav.ts`), `web/src/screens/Compare.tsx`, `web/src/screens/History.tsx` |
| Profile | `web/src/screens/Profile.tsx` |
| Landing | `web/src/screens/Landing.tsx`, `web/src/landing.css`, `web/src/landingExample.ts`, `web/src/landingScore.ts` |
| Onboarding | `web/src/screens/Onboarding.tsx` |
| Nutrition summary card | `web/src/KnowCard.tsx` |
| Where-to-buy block | `web/src/Where.tsx` |
| Score explanations | `web/src/PqExplain.tsx`, `web/src/verdict.ts` |
| Shared UI kit | `web/src/ui/index.tsx` (exports `Bar, Button, Card, Collapsible, Muted, NovaBadge, AmountScale, NutriScore, Pill, Row, Screen, NavBar, Segmented, Sheet, Skeleton, Loader, ChainLogo`, …) |
| Styles | `web/src/index.css`, `web/src/landing.css` |
| Alternatives data/prefetch | `web/src/alternatives.ts` |
| API client | `web/src/api/` (client calls `api.getProduct`, `api.getWebPriceQuick`, `api.addScan`, …) |

Note: imports in screens use `@shared/...` paths — check `web/tsconfig`/vite alias and the `shared/` package at repo root before assuming a file lives in `web/src`.

## 2. Phase 1 — Product page (`web/src/screens/Product.tsx`) — highest priority

Current problems: product identity can be pushed below `soldInFrance` warning cards; two large scores in the header; `KnowCard` + score flags + detailed nutrition/additive sections repeat each other; up to six warning rows; alternatives CTA not dominant.

Target structure (top → bottom):

1. `NavBar` (keep `SaveButton` on the right).
2. **Product identity first**: image, brand, name, pack size (`quantity`). Move the `soldInFrance` warning `Card` (currently ~line 100) *below* the identity block — keep it, it carries market-relevant info.
3. **Price**: one compact line — `2,49 €` + muted `· Estimated price · source details`. Reuse `priceHeadline(d.price_context)` / `packOf` / `packTxt` helpers already in the file. Keep source/reliability accessible via tap (existing `Sheet` pattern) or a muted second line — not a separate card.
4. **Quality score only**: keep the existing score component, remove the large Value score from the header. Value is a *comparison* metric and belongs in Alternatives.
5. **"What to know"**: 1–2 genuinely important observations (pick top 1–2 from existing `p.score`/`p.fit` data; do not fabricate). If `KnowCard` already covers this, drop `KnowCard` and render those observations as plain text rows — do not show both.
6. **Safety exception**: allergen/dietary-conflict warnings (hard exclusions per AGENTS.md core principles) must remain prominent — a card or warning-toned row above the fold. Never hide these for cleanliness.
7. **Primary action**: one obvious "Find better alternatives" button → `go(routes.alternatives)` (check actual route name in `nav.ts`). Make it the single `primary` button on the page.
8. Everything else (`Nutrition details`, `Additives and ingredients`, `Where to buy` → `Where.tsx`, NOVA, `PqExplain`, `Segmented` basis switcher) stays inside `Collapsible`/`Sheet`, **collapsed by default**. Keep the `basis` (`100`/`serving`/`pack`) switcher working inside the collapsed nutrition section.

Explicit removals/merges:
- One score in the header (Quality). Value score → Alternatives only.
- `KnowCard` removed *if* its content is represented elsewhere; otherwise keep it but remove the duplicate flag rows it summarizes.
- Cap visible warning/flag rows at 2; the rest go inside collapsed details.
- Do not remove: `SaveButton`, `Where`, offline pill, `DesktopQRBanner`, error/404 states, `prefetchAlternatives` effect, `getWebPriceQuick` lookup.

Acceptance:
- At 390px width, product name + quality score + price + one CTA visible without scrolling past warning cards.
- No two score blocks compete in the header.
- Allergen/dietary conflict still visible above the fold.
- `npm run build` (and `npm test` if present) passes; existing `__tests__` still green.

## 3. Phase 1 — Alternatives (`web/src/screens/Alternatives.tsx` + `web/src/alternatives.ts`) — highest priority

Current problems: each row shows quality score + value score + retailer logo stack + price + price delta + opens an intermediary `Sheet`; price search runs for up to 12 candidates × 4 concurrent even though only 3 are shown.

Target row (flat row, hairline separators, small consistent image ~56–64px):

- Image, name (2-line clamp), brand.
- **Quality mode**: quality score (e.g. `86/100 quality`) as the primary number; one short reason it is better; price/unit price + delta (e.g. `−18%`) in secondary text.
- **Value mode**: unit price (e.g. `3,20 €/kg`) as primary; delta vs original product; quality score in secondary text.
- Remove from default rows: `ChainLogo` stacks, secondary score tiles, repeated confidence labels, long explanations. Retailer logos move to the product page's `Where` block / detail view.
- Keep the existing `Segmented` Quality/Value toggle (two modes only — do not add more).
- **Tap row → product page directly.** Delete the intermediary detail sheet *only if* it purely repeats row data; if it carries unique info (full nutrition, where-to-buy), keep it but make it reachable from the product page instead. Prefer direct navigation: `go(routes.product(id))`.
- Initially show **3 alternatives** + "See more alternatives" expanding to 10 max.

Price-search change (`alternatives.ts`):
- Search prices only for the first 3 candidates on load. When the user expands the list, search the remaining candidates (up to 10) then — either a second request or lazy per-batch calls, matching existing API shape. Cap concurrency as today (4). This reduces initial latency and API cost; do not change backend endpoints unless required.

Acceptance:
- Default list: 3 flat rows, one number each, no logo stack.
- Row tap reaches the alternative's product page in one interaction.
- Prices for rows 4–10 load only after expand; skeleton/loading state for those rows until resolved.
- Quality and Value modes each show their designated primary metric.

## 4. Phase 2 — Scanner (`web/src/screens/Scan.tsx`, `web/src/ScanPeek.tsx`)

- Result preview (`ScanPeek`): remove the second large score (price-quality); keep quality score + product identity + "View product" as the clear action.
- Preview persists until user dismisses or scans another item — **remove the 7-second auto-dismiss**.
- Gallery/manual entry stays accessible; add a small manual product-search fallback for users who can't scan (link to existing search if present, else minimal text input hitting the same product lookup endpoint).
- Camera permission failure: show recoverable state ("Allow camera access" button re-requesting permission + gallery fallback); never require reload.
- Keep camera-first auto-open.

## 5. Phase 2 — Where to buy (`web/src/Where.tsx`)

Separate three distinct facts: online price found, retailers listing the product, nearby branch + confirmed stock.

- Show closest relevant retailer first; then a simple list of other retailers.
- Distance + unit price in the same row; branch address/directions secondary.
- Do not render five retailer logos beside alternatives — logo info lives here and on the product page.
- Do not claim stock/price that isn't confirmed (AGENTS.md: no unverified price claims).

## 6. Phase 3 — Saved, Profile, Landing, Onboarding

**Saved/List** (`screens/List.tsx`):
- Saved products as the main content; each item a simple row with discreet quality score.
- Move Compare and History into secondary nav (check `nav.ts` for existing routes `/compare`, `/history`).
- Empty state: one instruction — "Scan a product to start saving it."
- Naming: if it isn't a shopping list, call it "Saved" in UI copy (check `t()` keys in `web/src/i18n`).

**Profile** (`screens/Profile.tsx`):
- Group into three areas: *Shopping preferences* (location, supermarkets), *Food preferences* (diet, allergies/restrictions), *App settings* (language, account & data).
- Location and supermarket preferences optional; remove unnecessary personal fields.
- Keep existing functionality — this is regrouping + copy, not feature removal.

**Landing** (`screens/Landing.tsx`, `landing.css`):
- Shorten to: headline (one benefit) → one product comparison → three steps → one CTA.
- Move/remove the Yuka comparison section (can go lower or be cut).
- Keep the restrained visual style; reuse the same tokens as the app.

**Onboarding** (`screens/Onboarding.tsx`):
- Get to the scanner fast: default market France (`country` default already FR — verify), language selectable but not blocking, no forced account creation or preference setup.

## 7. Phase 3 — Design system cleanup (`web/src/index.css`, `web/src/ui/index.tsx`)

Known issue: repeated/overridden rules — `.card`, `.screen`, `.navbar`, `.twoscores`, `.arow`, `.ameta` defined more than once with different radius/shadow values.

Rules:
- Consolidate each class to a single definition; delete dead overrides.
- Establish tokens (CSS custom properties already partially exist — `--ink`, `--accent`, `--olive`, `--clay`, `--warn`, `--bad`): add/confirm `--bg`, `--fg`, `--muted`, `--line` (divider), spacing scale (`--s1..--s6` or similar), one radius scale, two button styles (primary forest-green filled, secondary outlined/plain).
- Cards only for warnings/exceptional info; flat rows + hairlines elsewhere.
- Replace inline `style={{...}}` where a shared class exists (Product.tsx error/empty states have several).
- Keep dark mode consistent with the same hierarchy (check for existing dark tokens before adding).
- Touch targets ≥44px; test wrapping/overflow at 375, 390, 430px widths.
- `landing.css` and `index.css` share tokens — no divergent palettes.

## 8. Explicit non-goals / constraints

- Do not change scoring logic, nutrient handling, allergen rules, or API contracts (AGENTS.md core principles are load-bearing: null ≠ 0, allergens hard-exclude, per-100g comparisons, no unverified price claims).
- Do not remove: `SaveButton`, `Where`, offline handling, error/404/retry states, `prefetchAlternatives`, `getWebPriceQuick`, `Segmented` two-mode toggle, i18n (`t()` keys — add keys for new copy rather than hardcoding strings; check `web/src/i18n`).
- Backend changes only if a frontend requirement genuinely needs one (e.g., a batch price endpoint for expanded alternatives) — prefer composing existing endpoints.
- No new dependencies without checking `web/package.json` first.

## 9. Verification

```bash
cd web
npm install        # if needed
npm run build      # must pass (tsc + vite)
npm test           # if test script exists — keep __tests__ green
npm run dev        # manual check at 375/390/430px widths
```

Backend untouched → backend tests not required, but run `cd backend && python -m pytest` if any API file changes.

Manual checklist per phase:
- Product: name/score/price/CTA above the fold; allergen warnings still prominent; collapsed sections expand correctly; basis switcher works.
- Alternatives: 3 rows → expand → 10; prices lazy-load on expand; Quality vs Value modes correct; row tap → product page.
- Scan: preview persists; no second score; dismiss + rescan works; permission-denied path recoverable.

## 10. Suggested commit slicing

1. `web: simplify product page hierarchy` (Phase 1a)
2. `web: flatten alternatives rows, lazy price search` (Phase 1b)
3. `web: persistent scan preview + manual search fallback` (Phase 2a)
4. `web: regroup where-to-buy / saved / profile` (Phase 2b–3)
5. `web: consolidate css tokens and remove duplicate rules` (Phase 3)
6. `web: shorten landing + faster onboarding` (Phase 3)
