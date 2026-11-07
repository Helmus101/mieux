"""Adds retailer price exports (JSON lists with chain, storeExtId, ean, price, updatedAt) to Mieux's local prices table, next to Open Prices.

    cd backend && .venv/bin/python -m scripts.import_store_prices ~/Downloads/dataset_monoprix-scraper_*.json ~/Downloads/dataset_intermarche-scraper_*.json

Rows get ids starting with "sc-"; re-running replaces the previous rows of the same chain, so it is safe to repeat. Run it again after each
Open Prices import (that import rebuilds the table). Prices are the pack price of one barcode in one store, dated by the export's updatedAt."""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OP_LOCAL", os.path.join(HERE, "op_local.db"))


def code_of(ean: str) -> str:
    e = "".join(ch for ch in str(ean or "") if ch.isdigit())
    return e[1:] if len(e) == 14 and e.startswith("0") else e


def main(paths, out: str = OUT) -> None:
    db = sqlite3.connect(out)
    for path in paths:
        rows = json.load(open(path, encoding="utf-8"))
        chain = rows[0]["chain"] if rows else None
        if not chain:
            continue
        db.execute("delete from op_items where json_extract(data, '$.id') like ?", (f"sc-{chain}-%",))
        batch, seen = [], set()
        for r in rows:
            code, price = code_of(r.get("ean")), r.get("price")
            if not code or price in (None, "") or r.get("status") not in (None, "ACTIVE") or (code, r.get("storeExtId")) in seen:
                continue
            seen.add((code, r.get("storeExtId")))
            date = (r.get("updatedAt") or "")[:10]
            loc = {"id": f"sc-{chain}-{r.get('storeExtId')}", "osm_id": None, "osm_brand": chain, "osm_name": r.get("storeName"), "osm_address_country_code": "FR",
                   "osm_lat": None, "osm_lon": None, "osm_address_city": r.get("storeAddress")}
            item = {"id": f"sc-{chain}-{r.get('storeExtId')}-{code}", "product_code": code, "price": price, "currency": r.get("currency") or "EUR", "price_per": None,
                    "date": date, "price_is_discounted": bool(r.get("promoted")), "location": loc}
            batch.append((code, date, json.dumps(item, separators=(",", ":"))))
        db.executemany("insert into op_items values (?,?,?)", batch)
        print(f"{chain}: {len(batch):,} prices")
    db.commit()
    db.close()


if __name__ == "__main__":
    main(sys.argv[1:])
