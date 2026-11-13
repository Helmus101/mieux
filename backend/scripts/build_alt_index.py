"""Build alt_index.db: the alternatives database.

A product is in it only if it can be recommended today: it has a brand, at least one supermarket chain, and a real observed
price (Open Prices / retailer data, per 100 g or ml). Everything else stays in the scan-lookup databases (off_local.db, op_local.db).

Run it after every Open Food Facts import and every price refresh (a few minutes):

    cd backend && . .venv/bin/activate && python -m scripts.build_alt_index
    OFF_LOCAL=$PWD/off_local_us.db OP_LOCAL=$PWD/op_local_us.db ALT_INDEX=$PWD/alt_index_us.db MARKET=US python -m scripts.build_alt_index

The API reads it through app/altindex.py; without the file it falls back to searching Open Food Facts category by category.
"""
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("JWT_SECRET_KEY", "build-alt-index")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(__import__("tempfile").gettempdir(), "build_alt_index_app.db")  # importing the API opens its app database: always a throwaway one, never the live one

MARKET = os.environ.get("MARKET", "FR").upper()
SRC = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db" if MARKET == "FR" else "off_local_us.db"))
OPS = os.environ.get("OP_LOCAL", os.path.join(HERE, "op_local.db" if MARKET == "FR" else "op_local_us.db"))
DST = os.environ.get("ALT_INDEX", os.path.join(HERE, "alt_index.db" if MARKET == "FR" else "alt_index_us.db"))
MIN_PER100 = 3.0          # cents per 100 g/ml: below this the price or the pack size is a data error


def main() -> None:
    for path in (SRC, OPS):
        if not os.path.exists(path):
            sys.exit(f"missing {path}")
    from app import market, taxo1000, taxonomy, value
    from app import main as api
    from app.products import normalize

    market.set_current(MARKET)
    prices = value.OpenPricesClient(local_path=OPS, country=MARKET, base="EUR" if MARKET == "FR" else "USD")
    src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True)
    ops = sqlite3.connect(f"file:{OPS}?mode=ro", uri=True)
    codes = [r[0] for r in ops.execute("select distinct code from op_items")]
    tmp = DST + ".new"
    if os.path.exists(tmp):
        os.remove(tmp)
    dst = sqlite3.connect(tmp)
    dst.executescript("""
        create table alt (code text primary key, brand text not null, name text not null, type text, per100 real not null, pack_cents integer,
                          amount real not null, unit text not null, price_date text not null, price_stale integer not null, chains text not null, scans integer);
        create table alt_cat (tag text, code text);
        create table alt_tax (grp text, code text);
    """)
    t0, kept, why = time.time(), 0, {}

    def skip(reason: str) -> None:
        why[reason] = why.get(reason, 0) + 1

    for n, code in enumerate(codes, 1):
        row = src.execute("select scans, data from off_products where code=?", (code,)).fetchone()
        if not row:
            skip("not_in_off")
            continue
        try:
            p = normalize(json.loads(row[1]))
        except Exception:
            skip("unreadable")
            continue
        q = p.get("quantity")
        brand = str(p.get("brand") or "").strip()
        name = str(p.get("name") or "").strip()
        if not name or " / " in name:
            skip("no_name")
        elif not brand:
            skip("no_brand")
        elif api._EXCLUDED_BRANDS.search(brand + " " + name):
            skip("excluded_brand")
        elif not q:
            skip("no_pack_size")
        else:
            pt = prices.latest(code, (q["amount"], q["unit"]), 730)
            if not pt or pt.get("per100_cents") is None or pt["per100_cents"] < MIN_PER100:
                skip("no_price")
                continue
            chains = api._candidate_chain_ids(p, prices.chain_summary)
            if not chains:
                skip("no_chain")
                continue
            tx = taxonomy.classify(p).get("type")
            groups = (taxo1000.classify(name, None, brand).get("groups") or [])[:3]
            dst.execute("insert into alt values (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (code, brand, name, tx, pt["per100_cents"], pt.get("pack_cents"), q["amount"], q["unit"], pt["date"],
                         1 if pt.get("stale") else 0, json.dumps(chains), row[0] or 0))
            dst.executemany("insert into alt_cat values (?,?)", [(t, code) for t in (p.get("categories") or [])])
            dst.executemany("insert into alt_tax values (?,?)", [(g, code) for g in groups])
            kept += 1
        if n % 5000 == 0:
            print(f"  {n}/{len(codes)} read, {kept} kept ({time.time() - t0:.0f} s)", flush=True)
    dst.executescript("create index alt_type on alt(type); create index alt_cat_tag on alt_cat(tag); create index alt_tax_grp on alt_tax(grp);")
    dst.commit()
    dst.close()
    os.replace(tmp, DST)      # swapped atomically: the API reopens the file when it changes
    print(f"done: {kept} of {len(codes)} priced products kept -> {DST} ({time.time() - t0:.0f} s)")
    for reason, count in sorted(why.items(), key=lambda kv: -kv[1]):
        print(f"  left out, {reason}: {count}")


if __name__ == "__main__":
    main()
