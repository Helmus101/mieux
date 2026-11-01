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
- `OFF_USER_AGENT` - User agent for Open Food Facts API

## Deployment

Backend can be deployed via:
- Railway (use `railway.json` or `nixpacks.toml`)
- Docker (use `Dockerfile`)
- Any Python hosting service

Web app deploys to Vercel/Netlify via `npm run build`.

Mobile app deploys via Expo EAS.

## PWA & Sound/Haptics

The PWA (index.html) includes:
- Haptic feedback via Web Vibration API
- Sound effects via Web Audio API (synthetic beeps)
- Barcode scanning sound on successful scan
- Service worker for offline support (web/public/sw.js)
- PWA manifest (manifest.json)

Web app (Vite/React) includes:
- Haptic feedback via haptics.ts
- Sound effects via sound.ts (Web Audio API)
- Sound on barcode scan

Mobile app (Expo) includes:
- Haptic feedback via expo-haptics
- Sound effects via expo-av (planned)
- Sound on barcode scan

## Quick Start

```bash
# Start backend only (includes PWA at /index.html)
./start.sh

# Or start backend manually
cd backend
source .venv/bin/activate
DATABASE_URL=sqlite:///./foodiq.db uvicorn app.main:app --reload

# Access PWA: http://localhost:8010/index.html
# Access API: http://localhost:8010
# Access API docs: http://localhost:8010/docs
```
