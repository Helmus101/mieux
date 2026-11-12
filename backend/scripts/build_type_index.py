"""Index every local Open Food Facts product by its Mieux product type.

OFF's own categories_tags are missing on a large share of records. This side table gives retrieval a specific,
stable category (`herbal_lozenge`, `plain_yogurt`, ...) even when OFF has no usable tags. It is rebuilt after
scripts/import_off_dump.py; the API simply has fewer type-indexed candidates until it runs.

    cd backend && .venv/bin/python -m scripts.build_type_index [--min-scans 1] [--limit N]
"""
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
BATCH = 5000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-scans", type=int, default=0, help="only index products scanned at least this often (0 = whole DB)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N products (for smoke tests)")
    args = ap.parse_args()
    if not os.path.exists(OFF):
        sys.exit(f"no Open Food Facts copy at {OFF}")

    from app import taxonomy
    db = sqlite3.connect(OFF)
    db.execute("create table if not exists off_type (code text primary key, type text, family text, category text, subcategory text, form text, use text, confidence text, scans integer)")
    db.execute("create index if not exists off_type_type on off_type (type, scans desc)")
    t0, n, written = time.time(), 0, 0
    buf = []

    def flush() -> None:
        nonlocal buf, written
        if not buf:
            return
        db.executemany("insert or replace into off_type values (?,?,?,?,?,?,?,?,?)", buf)
        db.commit()
        written += len(buf)
        buf = []

    sql = "select code, scans, data from off_products"
    if args.min_scans:
        sql += f" where scans >= {int(args.min_scans)}"
    for code, scans, data in db.execute(sql):
        n += 1
        try:
            r = json.loads(data)
        except ValueError:
            continue
        p = {"categories": r.get("categories_tags") or [], "name": r.get("product_name"), "brand": r.get("brands"), "generic_name": r.get("generic_name")}
        cl = taxonomy.classify(p)
        if cl.get("type"):
            buf.append((code, cl["type"], cl.get("family"), cl.get("category"), cl.get("subcategory"), cl.get("form"), cl.get("use"), cl.get("confidence"), scans or 0))
        if len(buf) >= BATCH:
            flush()
            print(f"  {n} read, {written} typed ({time.time() - t0:.0f} s)", flush=True)
        if args.limit and n >= args.limit:
            break
    flush()
    db.commit()
    print(f"done: {written} typed products from {n} read -> off_type in {OFF} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
