# Price data runbook

Prices come from two sources that are always used together: Open Prices (daily export) and retailer exports (JSON files from the scrapers).

## Add retailer files
1. Upload to the server volume as `/data/up_<name>.json` (`fly ssh sftp shell -a mieux-api`, `put file.json /data/up_file.json`). The Fly machine stops after deploys: `fly machine start 867543ae707348 -a mieux-api`.
2. Back up: `fly ssh console -a mieux-api -C "cp /data/op_local.db /data/op_local.db.bak"`.
3. Import (replaces each chain's old rows, drops barcodes that are not French products, dates undated files by file date):
   `fly ssh console -a mieux-api -C "sh -c 'cd /app && OP_LOCAL=/data/op_local.db python -m scripts.import_store_prices /data/up_*.json'"`
4. Rebuild the brand-to-chains list: `... python -m scripts.build_brand_chains 2000` (writes `brand_chains.json` next to the scripts; copy to `/data/brand_chains.json`).

## Refresh Open Prices
`python -m scripts.import_prices_dump` rebuilds the table but keeps the retailer rows (ids starting `sc-`).

## Notes
- Supported shapes: Monoprix/Intermarché/Leclerc/Carrefour/Lidl/Naturalia exports and the `{source, postal_code, products:[...]}` shape (Auchan, Lidl food, Biocoop). See `normalise()` in `scripts/import_store_prices.py`.
- Local/dev: `cd backend && .venv/bin/python -m scripts.import_store_prices ~/Downloads/*.json`.

## Readiness checks (run after every deploy and every data refresh)

```bash
cd backend
JWT_SECRET_KEY=t .venv/bin/python3.9 -m pytest -q                 # unit and integrity tests
.venv/bin/python3.9 -m scripts.alt_readiness                       # 50-product panel against https://mieux-api.fly.dev (add a base URL to test another host, --limit N for a quick run)
curl -s https://mieux-api.fly.dev/health/ready                     # database, Open Food Facts copy, search providers, searches today / daily cap
```

`alt_readiness` exits 1 on any broken promise: a tab over 20 items, a duplicate, the scanned product itself, a product not sold in France or at no chain, a level 3-4 substitute,
a "cheaper" item that is not cheaper, a better price-quality / quality item that is not better, or a web price not flagged approximate. It also prints how many products fill all three
tabs to 10 and the latency p50 / p95. `fly.toml` health-checks `/health/ready`, so a deploy that cannot open its databases never replaces the running machine.
