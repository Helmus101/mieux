# Running Mieux for many people, on any device

One server serves both the API and the web app, so any phone or computer just opens its address.

## 1. Data (no rate limits)
Open Food Facts and Open Prices both allow live calls only at a few per minute per address and block clients that push. Mieux therefore keeps its own copy:

    ./update_data.sh ~/Downloads/en.openfoodfacts.org.products.csv   # monthly (https://world.openfoodfacts.org/data), also prices
    ./update_data.sh                                                  # prices only, daily or weekly

This builds `backend/off_local.db` (about 1,1 million French products) and `backend/op_local.db` (French shop prices). The live APIs are only a fallback for products newer than the export.
Data: Open Food Facts contributors, ODbL. Keep the attribution in the app.

## 2. Build and run
    cd web && npm run build            # creates web/dist, served by the backend
    cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010

## 3. Phones need HTTPS for the camera
Browsers only allow the camera on https:// (or localhost). On a home network `http://192.168.x.x:8010` loads the app but the camera stays blocked, so type the barcode instead.
To get the camera on any phone, publish the server behind HTTPS: a host such as Railway or Render (the Dockerfile in backend/ works, copy the two .db files and web/dist into the image or a volume),
or a quick tunnel for testing: `cloudflared tunnel --url http://localhost:8010`.

## 4. For hundreds of users
SQLite is fine for the local data copies (read-only). For the user data (sessions, history, prices) set `DATABASE_URL` to PostgreSQL. Run several uvicorn workers (`--workers 4`).
