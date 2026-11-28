"""Re-place only the products whose OFF record matches a text filter, after a rule fix (a full build_taxonomy_index takes ~20 min).

  cd backend && .venv/bin/python -m scripts.reclassify_subset saumon salmon [--dry-run]

Before writing, the subset's current rows are copied to off_taxo_bak_<timestamp> / off_tax_bak_<timestamp> (the way back:
delete the subset's rows from off_taxo / off_tax and insert the backup rows). Same classifier call as build_taxonomy_index."""
import argparse
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="+", help="substrings looked for in the product record (case-insensitive)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    from app import taxo1000
    db = sqlite3.connect(OFF)
    cond = " or ".join("lower(data) like ?" for _ in args.words)
    rows = db.execute(f"select code, scans, data from off_products where {cond}", [f"%{w.lower()}%" for w in args.words]).fetchall()
    print(f"{len(rows)} products match")
    new, changed = [], 0
    old = {c: t for c, t in db.execute("select code, type from off_taxo where code in (select code from off_products where " + cond + ")", [f"%{w.lower()}%" for w in args.words])}
    for code, scans, data in rows:
        try:
            r = json.loads(data)
        except ValueError:
            continue
        cl = taxo1000.classify(r.get("product_name"), r.get("generic_name"), r.get("brands"), r.get("categories_tags"))
        new.append((code, scans or 0, cl))
        changed += old.get(code) != cl.get("type")
    print(f"{changed} change type")
    if args.dry_run:
        return
    ts = time.strftime("%Y%m%d%H%M%S")
    codes = [c for c, _, _ in new]
    db.execute(f"create table off_taxo_bak_{ts} as select * from off_taxo where 0")
    db.execute(f"create table off_tax_bak_{ts} as select * from off_tax where 0")
    for i in range(0, len(codes), 500):
        q = ",".join("?" * len(codes[i:i + 500]))
        db.execute(f"insert into off_taxo_bak_{ts} select * from off_taxo where code in ({q})", codes[i:i + 500])
        db.execute(f"insert into off_tax_bak_{ts} select * from off_tax where code in ({q})", codes[i:i + 500])
        db.execute(f"delete from off_tax where code in ({q})", codes[i:i + 500])
    for code, scans, cl in new:
        db.execute("insert or replace into off_taxo values (?,?,?,?,?,?,?)", (code, cl.get("type"), cl.get("category"), cl.get("department"), cl.get("level") or 0, cl.get("source"), scans))
        for grp in cl.get("groups") or []:
            db.execute("insert or replace into off_tax values (?,?,?,?)", (code, grp, cl.get("type"), scans))
    db.commit()
    print(f"done; backup tables off_taxo_bak_{ts}, off_tax_bak_{ts}")


if __name__ == "__main__":
    main()
