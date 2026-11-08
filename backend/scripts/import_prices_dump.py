"""Build Mieux's own copy of the Open Prices data for one country (France by default) from the official daily exports (no API, no rate limit).

    cd backend && .venv/bin/python -m scripts.import_prices_dump            # downloads prices.jsonl.gz + locations.jsonl.gz, then imports
    cd backend && .venv/bin/python -m scripts.import_prices_dump data/prices.jsonl.gz data/locations.jsonl.gz

The two files are published at https://prices.openfoodfacts.org/data/ and refreshed daily; run this daily or weekly (it replaces the table atomically).
Only prices recorded in shops of that country are kept. For the United States, with the files already in backend/data:

    OP_COUNTRY=US OP_LOCAL=$PWD/op_local_us.db .venv/bin/python -m scripts.import_prices_dump data/prices.jsonl.gz data/locations.jsonl.gz
 Source and licence: Open Prices / Open Food Facts contributors (ODbL)."""
import gzip
import json
import os
import sqlite3
import sys
import time
import urllib.request

BASE = "https://prices.openfoodfacts.org/data/"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTRY = os.environ.get("OP_COUNTRY", "FR").upper()  # ISO code of the shops to keep
OUT = os.environ.get("OP_LOCAL", os.path.join(HERE, "op_local.db"))


def fetch(name: str) -> str:
    path = os.path.join(HERE, "data", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "Mieux/0.2 (prototype)"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def main(prices_path: str, locations_path: str, out: str = OUT) -> None:
    t0 = time.time()
    locs = {}
    with gzip.open(locations_path, "rt", encoding="utf-8") as f:
        for line in f:
            L = json.loads(line)
            if (L.get("osm_address_country_code") or "").upper() == COUNTRY:
                locs[L["id"]] = {"id": L["id"], "osm_id": L.get("osm_id"), "osm_brand": L.get("osm_brand"), "osm_name": L.get("osm_name"), "osm_address_country_code": COUNTRY,
                                 "osm_lat": L.get("osm_lat"), "osm_lon": L.get("osm_lon"), "osm_address_city": L.get("osm_address_city")}
    tmp = out + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.execute("create table op_items (code text, date text, data text)")
    n = 0
    batch = []
    with gzip.open(prices_path, "rt", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            loc = locs.get(p.get("location_id"))
            if not loc or not p.get("product_code") or p.get("price") in (None, ""):
                continue
            item = {"id": p["id"], "product_code": p["product_code"], "price": p["price"], "currency": p.get("currency") or ("USD" if COUNTRY == "US" else "EUR"), "price_per": p.get("price_per"),
                    "date": p.get("date"), "price_is_discounted": bool(p.get("price_is_discounted")), "location": loc}
            batch.append((p["product_code"], p.get("date") or "", json.dumps(item, separators=(",", ":"))))
            n += 1
            if len(batch) >= 20000:
                db.executemany("insert into op_items values (?,?,?)", batch)
                batch = []
    db.executemany("insert into op_items values (?,?,?)", batch)
    # Retailer exports added by import_store_prices.py (ids "sc-...") live in the same table; carry them over so a refresh never drops them.
    if os.path.exists(out):
        try:
            old = sqlite3.connect(out)
            keep = old.execute("select code, date, data from op_items where json_extract(data, '$.id') like 'sc-%'").fetchall()
            old.close()
            db.executemany("insert into op_items values (?,?,?)", keep)
            print(f"kept {len(keep):,} retailer prices")
        except sqlite3.Error:
            pass
    db.execute("create index op_code on op_items (code, date desc)")
    db.commit()
    db.close()
    os.replace(tmp, out)
    print(f"done: {n:,} prices in {len(locs):,} {COUNTRY} shops -> {out}  ({time.time() - t0:0.0f}s)")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    else:
        main(fetch("prices.jsonl.gz"), fetch("locations.jsonl.gz"))
