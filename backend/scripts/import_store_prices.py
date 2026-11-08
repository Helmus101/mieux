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


def parse_price(v):
    """'2,39€', '24,03 €', 7.99 -> float, else None."""
    if isinstance(v, (int, float)):
        return float(v)
    t = "".join(ch for ch in str(v or "") if ch.isdigit() or ch in ",.").replace(",", ".")
    try:
        return float(t) if t else None
    except ValueError:
        return None


def normalise(r: dict, path: str) -> dict:
    """Other exports (Picard, Carrefour online) to the common shape: chain, storeExtId, ean, price, updatedAt. Loyalty promotions are ignored: the shelf price is kept."""
    if "chain" in r:
        return r
    date = r.get("scrapedAt") or __import__("datetime").datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
    if "productId" in r:      # Picard
        return {"chain": "Picard", "storeExtId": "picard-online", "storeName": "Picard.fr", "storeAddress": "France", "ean": r.get("ean"), "price": r.get("price"),
                "currency": r.get("priceCurrency"), "status": "ACTIVE" if r.get("inStock", True) else "OUT", "updatedAt": date}
    if "product_name" in r and "ean" in r:     # E.Leclerc online, name/price/ean export
        price = parse_price(r.get("price"))
        if price is None:
            return {}
        return {"chain": "E.Leclerc", "storeExtId": "leclerc-online", "storeName": "E.Leclerc en ligne", "storeAddress": "France", "ean": r.get("ean"), "price": price,
                "currency": "EUR", "status": "ACTIVE", "updatedAt": date}
    if "lidl" in os.path.basename(path).lower() and "name" in r:     # Lidl online, name/price/ean export
        price = parse_price(r.get("price"))
        return {} if price is None else {"chain": "Lidl", "storeExtId": "lidl-online", "storeName": "Lidl en ligne", "storeAddress": "France", "ean": r.get("ean"),
                                         "price": price, "currency": "EUR", "status": "ACTIVE", "updatedAt": date}
    if "price_per_unit" in r and "name" in r:     # Intermarché online, name/price/ean export (no store given)
        price = parse_price(r.get("price"))
        return {} if price is None else {"chain": "Intermarché", "storeExtId": "intermarche-online", "storeName": "Intermarché en ligne", "storeAddress": "France",
                                         "ean": r.get("ean"), "price": price, "currency": "EUR", "status": "ACTIVE", "updatedAt": date}
    if "e.leclerc" in str(r.get("url")):      # E.Leclerc online; marketplace sellers are not Leclerc shelf prices
        if not str(r.get("seller") or "E.Leclerc").lower().startswith("e.leclerc"):
            return {}
        return {"chain": "E.Leclerc", "storeExtId": "leclerc-online", "storeName": "E.Leclerc en ligne", "storeAddress": "France", "ean": r.get("ean"), "price": r.get("price"),
                "currency": r.get("currency"), "status": "ACTIVE", "updatedAt": date}
    if r.get("isMarketplace") or r.get("businessType") == "non-food":
        return {}
    return {"chain": "Carrefour", "storeExtId": "carrefour-online", "storeName": "Carrefour.fr", "storeAddress": "France", "ean": r.get("ean"), "price": r.get("price"),
            "currency": r.get("currency"), "status": "ACTIVE" if r.get("available", True) else "OUT", "updatedAt": date}


def main(paths, out: str = OUT) -> None:
    db = sqlite3.connect(out)
    by_chain = {}
    for path in paths:
        for x in (normalise(r, path) for r in json.load(open(path, encoding="utf-8"))):
            if x:
                by_chain.setdefault(x["chain"], []).append(x)
    for chain, rows in by_chain.items():
        db.execute("delete from op_items where json_extract(data, '$.id') like ?", (f"sc-{chain}-%",))
        batch, seen = [], set()
        for r in rows:
            code, price = code_of(r.get("ean")), r.get("price")
            if len(code) < 8 or price in (None, "") or r.get("status") not in (None, "ACTIVE") or (code, r.get("storeExtId")) in seen:
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
