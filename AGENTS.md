# AGENTS.md

This file contains learned information about the Mieux project for AI agents.

## Project Overview

Mieux is a personalized grocery decision-support product with:
- Backend: FastAPI + SQLAlchemy (PostgreSQL/SQLite)
- Web: React + Vite + TypeScript
- Mobile: Expo + React Native (iOS first)
- Shared: TypeScript package for common code

## Commands

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./foodiq.db alembic upgrade head
python -m pytest
uvicorn app.main:app --reload
```

### Web App
```bash
cd web
npm install
npm run dev
```

### Mobile App
```bash
cd mobile
npm install
npx expo start
```

## Testing

Run backend tests:
```bash
cd backend
DATABASE_URL=sqlite:///./foodiq.db python -m pytest
```

All 9 tests should pass.

## Open Food Facts local copy and alternative search

The API reads products from `backend/off_local.db` (built by `scripts/import_off_dump.py`). Alternatives are chosen over
whole categories through the compact side index `backend/off_quick.db`; rebuild it after importing a new dump:

```bash
cd backend
. .venv/bin/activate
python scripts/build_quick_index.py     # ~20 s for 1.1 M products
python scripts/build_type_index.py      # indexes every product by Mieux type (off_type); run after the OFF import
```

Without those files the API still works: it falls back to OFF category tags and name search. `build_type_index.py`
matters most for the large share of OFF records that have no `categories_tags`; use `--min-scans 1` for a faster partial pass.

## Database Migrations

To create a new migration:
```bash
cd backend
alembic revision -m "description"
alembic upgrade head
```

## Core Principles

1. No hidden composite score
2. Missing nutrient values remain null (never treated as zero)
3. Allergens are hard exclusions
4. Unknown means unverified (not safe)
5. Alternatives must be same-category by default
6. Per-100g comparisons only
7. No unverified price claims
8. Purchases ≠ consumption
9. Deterministic receipt parsing (no LLM for arithmetic)
10. User must confirm receipt product matches

## Retailer-Specific Receipt Parsing

Supports 9 major French retailers:
- Carrefour, Monoprix, Leclerc, Auchan, Lidl
- Aldi, Intermarché, Franprix, Casino

Each has custom date patterns, total keywords, and skip keywords in `backend/app/receipts.py`.

## Authentication

Local JWT authentication (no external provider):
- `/v1/auth/login` - Get JWT token
- `/v1/auth/register` - Register new user
- Anonymous sessions via `X-Session-Id` header
- JWT secret in `JWT_SECRET_KEY` env var

## Environment Variables

Required for backend:
- `DATABASE_URL` - PostgreSQL or SQLite connection string
- `JWT_SECRET_KEY` - Secret for JWT tokens
- `ALLOWED_ORIGINS` - Comma-separated list of allowed CORS origins
- `OFF_USER_AGENT` - User agent for Open Food Facts
- `SUPABASE_URL` - Optional: enables Supabase sign-in token verification (`SUPABASE_JWT_SECRET` only for legacy HS256 projects) API
- Supabase also needs `backend/supabase/scan_counts.sql` run once (the per-account scan total)

## Deployment

Backend can be deployed via:
- Railway (use `railway.json` or `nixpacks.toml`)
- Docker (use `Dockerfile`)
- Any Python hosting service

Web app deploys to Vercel/Netlify via `npm run build`.

Mobile app deploys via Expo EAS.

## Markets (France and United States)

The app sends `X-Country: FR|US` on every call (profile setting, default FR). `app.state.off` forwards to that market's own Open Food Facts copy:
`off_local.db` + `off_quick.db` (France) and `off_local_us.db` + `off_quick_us.db` (United States). Build the US copy like the French one, with a country:

```bash
cd backend
OFF_COUNTRY=united-states OFF_LOCAL=$PWD/off_local_us.db .venv/bin/python3.9 -m scripts.import_off_dump ~/Downloads/en.openfoodfacts.org.products.csv
OFF_LOCAL=$PWD/off_local_us.db OFF_QUICK=$PWD/off_quick_us.db .venv/bin/python3.9 scripts/build_quick_index.py
```

`soldInFrance` on a product means "sold in the request's market" (name kept for cached rows). Chains live in `retail.py` / `chains.py`; `retail.in_market()` keeps each market's chain list separate. Community prices (Open Prices) are per market too: `op_local.db` (France, EUR) and `op_local_us.db` (US shops, USD), built with
`OP_COUNTRY=US OP_LOCAL=$PWD/op_local_us.db .venv/bin/python3.9 -m scripts.import_prices_dump data/prices.jsonl.gz data/locations.jsonl.gz`.
Prices are held in the market's currency (`market.currency()`), sentences are localised with `market.localize_money`, and category price estimates exist for France only.
Code that fans out to a `ThreadPoolExecutor` must use `_ctx_map` so worker threads keep the request's market.
