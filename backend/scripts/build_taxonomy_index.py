"""Index every local Open Food Facts product by the Mieux taxonomy (app/mieux_taxonomy.json + app/taxorules.py).

Writes, inside the OFF database next to `off_type`:
  off_taxo(code primary key, type, category, department, level, source, scans)   one row per product: level 3 = product type,
                                                                              2 = category only, 1 = department only, 0 = unclassified
  off_tax(code, grp, ptype, scans)                                              one row per (product, substitution group), as before

    cd backend && .venv/bin/python -m scripts.build_taxonomy_index [--min-scans 1] [--limit N] [--workers 8]
"""
import argparse
import json
import multiprocessing as mp
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
BATCH = 4000


def work(batch):
    from app import taxo1000
    out = []
    for code, scans, data in batch:
        try:
            r = json.loads(data)
        except ValueError:
            continue
        cl = taxo1000.classify(r.get("product_name"), r.get("generic_name"), r.get("brands"), r.get("categories_tags"))
        out.append((code, scans or 0, cl.get("type"), cl.get("category"), cl.get("department"), cl.get("level") or 0, cl.get("source"), cl.get("groups") or []))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-scans", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()
    if not os.path.exists(OFF):
        sys.exit(f"no Open Food Facts copy at {OFF}")
    db = sqlite3.connect(OFF)
    db.execute("create table if not exists off_tax (code text, grp text, ptype text, scans integer, primary key (code, grp))")
    db.execute("create index if not exists off_tax_grp on off_tax (grp, scans desc)")
    db.execute("create table if not exists off_taxo (code text primary key, type text, category text, department text, level integer, source text, scans integer)")
    db.execute("create index if not exists off_taxo_type on off_taxo (type, scans desc)")
    db.execute("create index if not exists off_taxo_cat on off_taxo (category, scans desc)")
    db.execute("delete from off_tax")
    db.execute("delete from off_taxo")
    sql = "select code, scans, data from off_products" + (f" where scans >= {int(args.min_scans)}" if args.min_scans else "")

    def batches():
        buf, n = [], 0
        rd = sqlite3.connect(OFF)        # the pool feeds from its own thread: it needs its own connection
        for row in rd.execute(sql):
            buf.append(row)
            n += 1
            if len(buf) >= BATCH:
                yield buf
                buf = []
            if args.limit and n >= args.limit:
                break
        if buf:
            yield buf

    t0, n, lv = time.time(), 0, {0: 0, 1: 0, 2: 0, 3: 0}
    with mp.Pool(args.workers) as pool:
        for res in pool.imap(work, batches(), chunksize=1):
            db.executemany("insert or replace into off_taxo values (?,?,?,?,?,?,?)", [(c, t, ca, d, l, s, sc) for c, sc, t, ca, d, l, s, g in res])
            db.executemany("insert or replace into off_tax values (?,?,?,?)", [(c, grp, t, sc) for c, sc, t, ca, d, l, s, g in res for grp in g])
            for r in res:
                lv[r[5]] = lv.get(r[5], 0) + 1
            n += len(res)
            db.commit()
            print(f"  {n} products ({time.time() - t0:.0f} s)", flush=True)
    print(f"done in {time.time() - t0:.0f} s: " + ", ".join(f"level {k}: {v} ({100 * v / max(1, n):.1f}%)" for k, v in sorted(lv.items(), reverse=True)))


if __name__ == "__main__":
    main()
