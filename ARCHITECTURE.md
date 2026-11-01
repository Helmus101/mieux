# Mieux architecture (as built)

```
Web/iOS home-screen app (index.html, PWA)  ──►  FastAPI backend (backend/app)  ──►  SQLite (PostgreSQL via DATABASE_URL)
   scan · result · choice engine UI                products · engine · receipts          users, preferences, products,
   receipts review · purchases · profile           │                                      product_snapshots, scans, comparisons,
   (works offline-of-backend: falls back to         └──► Open Food Facts (isolated in      alternatives, receipts, receipt_items,
    local logic when /v1/health is absent)               app/off.py)                      price_observations
```
| Module | Responsibility |
|---|---|
| `app/products.py` | Normalise OFF records; unknown nutrients stay `None`; data-quality flags |
| `app/off.py` | Only place that knows OFF URLs (swap search endpoint here) |
| `app/engine.py` | Candidates → hard restrictions → completeness → rank by priority order → explain. `fit()` for per-priority verdicts; `compare()` on a single per-100 g basis |
| `app/receipts.py` | Deterministic parsing (French decimals, totals/payments/subtotals skipped, discounts), candidate matching (never auto-links), integer cents |
| `app/main.py` | `/v1/products/{barcode}`, `/v1/search`, `/v1/scans`, `/v1/me/preferences`, `/v1/products/{barcode}/alternatives`, `/v1/comparisons`, `/v1/receipts/preview|confirm`, `/v1/receipts`, `/v1/purchases`, `DELETE /v1/receipts/{id}`, `/v1/me/export`, `DELETE /v1/me` |

Auth: anonymous `X-Session-Id` (accounts optional, not blocking scanning).
Rules enforced in code and tests: no hidden score; allergen/diet conflicts excluded; missing data = "cannot verify"; alternatives from the same category; per-100 g basis only; price claims not made (no reliable data); purchases ≠ consumption; deleting a receipt removes items and price observations.

Run: `./run.sh` → http://localhost:8010. Tests: `cd backend && .venv/bin/python -m pytest`.

## Not built yet (next steps)
Expo/React Native client (the PWA covers iOS now), Supabase auth, PostgreSQL migrations (Alembic), on-device ML Kit/Vision OCR (the web app uses Tesseract.js), retailer-specific receipt rules, Open Prices integration, rate limiting, CI.
