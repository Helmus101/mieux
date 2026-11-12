"""Index every local Open Food Facts product by the Mieux 1000+ taxonomy (app/mieux_taxonomy.json).

Writes one row per (product, substitution group) into `off_tax` inside the OFF database, next to `off_type`
(scripts/build_type_index.py). Run after scripts/import_off_dump.py; the API falls back to the other indexes until it runs.

    cd backend && .venv/bin/python -m scripts.build_taxonomy_index [--min-scans 1] [--limit N]
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

    from app import taxo1000
    db = sqlite3.connect(OFF)
    db.execute("create table if not exists off_tax (code text, grp text, ptype text, scans integer, primary key (code, grp))")
    db.execute("create index if not exists off_tax_grp on off_tax (grp, scans desc)")
    db.execute("delete from off_tax")          # full rebuild: stale assignments must not survive a taxonomy change
    t0, n, written = time.time(), 0, 0
    buf = []

    def flush() -> None:
        nonlocal buf, written
        if not buf:
            return
        db.executemany("insert or replace into off_tax values (?,?,?,?)", buf)
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
        cl = taxo1000.classify(r.get("product_name"), r.get("generic_name"))
        if cl.get("groups"):
            for g in cl["groups"]:
                buf.append((code, g, cl.get("type"), scans or 0))
        if len(buf) >= BATCH:
            flush()
            print(f"  {n} read, {written} rows ({time.time() - t0:.0f} s)", flush=True)
        if args.limit and n >= args.limit:
            break
    flush()
    db.commit()
    print(f"done: {written} taxonomy rows from {n} read -> off_tax in {OFF} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
