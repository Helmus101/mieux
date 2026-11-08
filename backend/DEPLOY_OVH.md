# Deploying the API on an OVH VPS

Supabase stays as it is (login and scan counts). Only the Python API and its databases move to the VPS.

## 1. What to buy
An OVH VPS with 2 vCPU, 4 GB RAM and at least 40 GB disk, Ubuntu 24.04 (1 vCPU / 2 GB also works but is tight). Note its public IP.

## 2. DNS
Create an `A` record `api.<your-domain>` pointing to the VPS IP (Caddy needs a real hostname to issue the HTTPS certificate).

## 3. Prepare the server (once)
```
ssh ubuntu@<ip>
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git rsync
sudo usermod -aG docker $USER && newgrp docker
sudo mkdir -p /srv/mieux/data && sudo chown $USER /srv/mieux/data
git clone <your repo url> mieux && cd mieux/backend/deploy
cp .env.example .env && nano .env        # fill API_DOMAIN, JWT_SECRET_KEY, ALLOWED_ORIGINS, keys
```

## 4. Copy the data from your laptop (about 1.8 GB, once)
```
cd backend
rsync -avP off_local.db off_quick.db op_local.db brand_chains.json value_reference.json ubuntu@<ip>:/srv/mieux/data/
```
(`foodiq.db` holds user data and the web-price cache is created by itself; the `*_us.db` files are not needed: the app is France only.)

## 5. Start
```
cd ~/mieux/backend/deploy && docker compose up -d --build
curl https://api.<your-domain>/health
```

## 6. Point the web app at it
In the repo-root `vercel.json` replace `https://mieux-api.fly.dev/v1/:path*` by `https://api.<your-domain>/v1/:path*`, commit, push. For the mobile app set the API base to the same address.

## 7. Updating
`cd ~/mieux && git pull && cd backend/deploy && docker compose up -d --build`

## 8. Price data
Retailer files: copy them to `/srv/mieux/data/up_*.json`, then
`docker compose exec api python -m scripts.import_store_prices /data/up_*.json` and
`docker compose exec api python -m scripts.build_brand_chains 2000` (see DATA_RUNBOOK.md).

## 9. Backups
Back up `/srv/mieux/data/mieux.db` (user accounts and history) daily, e.g. a cron with `sqlite3 /srv/mieux/data/mieux.db ".backup /srv/mieux/backup/mieux-$(date +%F).db"`. The OFF and price databases can be rebuilt from the public dumps.
