# Mieux

A personalized grocery decision-support product helping users make smarter food choices through barcode scanning, nutrition assessment, and purchase tracking.

## Architecture

### Backend (FastAPI + SQLAlchemy)
- **Location**: `backend/`
- **Database**: PostgreSQL (via Alembic migrations) or SQLite for local development
- **Authentication**: Local JWT tokens (no external auth provider)
- **Features**:
  - Product lookup via Open Food Facts API
  - Personalized nutrition assessment with allergen detection
  - Alternative product recommendations
  - Side-by-side product comparison
  - Receipt OCR parsing (retailer-specific for 9 major French retailers)
  - Purchase history and price tracking
  - Data export and account deletion (GDPR/CNIL compliant)

### Web App (React + Vite)
- **Location**: `web/`
- **Tech Stack**: React 18, TypeScript, Vite, React Router
- **Features**:
  - Barcode scanning with ZXing
  - Receipt OCR with Tesseract.js
  - Sound effects (Web Audio API)
  - Haptic feedback (Web Vibration API)
  - All backend features accessible via shared API client

### PWA (index.html)
- **Location**: Root `index.html`
- **Tech Stack**: Vanilla JavaScript
- **Features**:
  - Barcode scanning (ZXing UMD or native BarcodeDetector)
  - Receipt OCR (Tesseract.js CDN)
  - Sound effects (Web Audio API - synthetic beeps)
  - Haptic feedback (Web Vibration API)
  - Offline support (localStorage)
  - PWA manifest and service worker
  - Works directly at `http://localhost:8010/index.html`

### Mobile App (Expo + React Native)
- **Location**: `mobile/`
- **Tech Stack**: Expo SDK 50, React Native 0.73, Expo Router
- **Platform**: iOS first (managed workflow)
- **Features**:
  - Barcode scanning with expo-camera
  - Receipt capture with expo-image-picker
  - Haptic feedback (expo-haptics)
  - Sound effects (expo-av - implementation planned)
  - ML Kit Vision OCR (placeholder - needs implementation)
  - All backend features accessible via shared API client

### Shared Code
- **Location**: `shared/`
- **Purpose**: TypeScript types, API client, Zustand stores shared between web and mobile

## Quick Start

### Start Mieux

Run the root startup script to start the backend server:
```bash
./start.sh
```

This will:
- Create virtual environment if needed
- Install dependencies
- Run database migrations
- Start the backend server on http://localhost:8010 with auto-reload

**Access points:**
- API: http://localhost:8010
- API Docs: http://localhost:8010/docs
- Health: http://localhost:8010/health
- Readiness: http://localhost:8010/health/ready

### Verification

Run the verification script to check the backend is working:
```bash
./verify.sh
```

### Web App

```bash
cd web
npm install
npm run dev  # Starts on http://localhost:5173
```

### Mobile App

```bash
cd mobile
npm install
npx expo start  # Follow instructions for iOS simulator
```

## Environment Variables

Backend (`.env`):
```
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/foodiq
JWT_SECRET_KEY=your-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8010
OFF_USER_AGENT=Mieux/1.0 (contact@mieux.app)
```

## API Endpoints

- `GET /v1/products/{barcode}` - Get product details
- `GET /v1/search?q=` - Search products
- `POST /v1/scans` - Record a scan
- `GET /v1/scans` - Get scan history
- `GET/PUT /v1/me/preferences` - User preferences
- `POST /v1/products/{barcode}/alternatives` - Get alternatives
- `POST /v1/comparisons` - Compare products
- `POST /v1/receipts/preview` - Parse receipt
- `POST /v1/receipts/confirm` - Save receipt
- `GET /v1/receipts` - Get receipts
- `GET /v1/purchases` - Get purchase history
- `DELETE /v1/receipts/{id}` - Delete receipt
- `GET /v1/me/export` - Export user data
- `DELETE /v1/me` - Delete account
- `POST /v1/auth/login` - Login
- `POST /v1/auth/register` - Register
- `GET /health` - Health check
- `GET /health/ready` - Readiness check

## Sound & Haptics

### PWA (index.html)
- **Sound**: Web Audio API synthetic beeps on scan, success, error, tap
- **Haptics**: Web Vibration API (navigator.vibrate)
- **Feedback**:
  - Scan: High-pitched beep + short vibration
  - Success: Ascending tone + double-tap vibration
  - Error: Low buzz + long vibration pattern
  - Tap: Short click + light vibration

### Web App (Vite/React)
- **Sound**: Web Audio API via `src/sound.ts`
- **Haptics**: Web Vibration API via `src/haptics.ts`
- **Same feedback patterns as PWA**

### Mobile App (Expo)
- **Haptics**: expo-haptics (success, warning, error, light, medium, heavy)
- **Sound**: expo-av (implementation planned)
- **Haptic patterns configured in `src/haptics.ts`**

## Core Principles

1. **No hidden composite score** - Nutri-Score is displayed as recorded
2. **Missing values remain null** - Never treat missing nutrient values as zero
3. **Allergens are hard exclusions** - Always warn about declared allergens
4. **Unknown means unverified** - Missing ingredient data means "cannot verify", not safe
5. **Alternatives are comparable** - Same-category by default
6. **Per-100g comparisons** - All nutrition data normalized to 100g/100ml
7. **No unverified price claims** - Only receipt-derived prices are shown
8. **Purchases ≠ consumption** - Tracking what you buy, not what you eat
9. **Deterministic receipt parsing** - No LLM for arithmetic or money calculations
10. **User must confirm** - Receipt product matching is candidate-only, never automatic

## Retailer-Specific Receipt Parsing

Supports 9 major French retailers with custom parsing rules:
- Carrefour, Monoprix, Leclerc, Auchan, Lidl
- Aldi, Intermarché, Franprix, Casino

Each retailer has:
- Custom date pattern
- Custom total detection keywords
- Custom skip keywords for payment/tax lines

## Deployment

### Railway

1. Connect GitHub repository to Railway
2. Create PostgreSQL service
3. Create service for backend with `railway.json` or `nixpacks.toml`
4. Set environment variables
5. Deploy

### Web App

Deploy to Vercel, Netlify, or similar platforms:
```bash
cd web
npm run build
# Upload dist/ folder
```

### Mobile App

Build and deploy via Expo:
```bash
cd mobile
eas build --platform ios
```

## Testing

```bash
cd backend
python -m pytest  # Backend tests
```

## License

Internal project - See LICENSE file for details.
