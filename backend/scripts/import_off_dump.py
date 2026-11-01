"""Build Mieux's own copy of the French part of Open Food Facts from the official CSV export.

    cd backend && .venv/bin/python -m scripts.import_off_dump ~/Downloads/en.openfoodfacts.org.products.csv

Why: the live Open Food Facts API allows only ~10 searches and ~100 product reads per minute per address and blocks clients that push, so a
product used by hundreds of people cannot depend on it. With this copy, product lookups, category searches and name searches are local
database queries (instant, unlimited). The live API stays as a fallback for products newer than the dump. Re-run monthly with the new export:
the table is replaced atomically, so the app keeps working while it runs.
Source and licence: Open Food Facts, ODbL (attribute 'Open Food Facts contributors')."""
import json
import os
import re
import sqlite3
import sys
import time

import duckdb

OUT = os.environ.get("OFF_LOCAL", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "off_local.db"))
NUTRI = ["energy-kcal", "fat", "saturated-fat", "trans-fat", "carbohydrates", "sugars", "fiber", "proteins", "salt", "sodium", "vitamin-a", "vitamin-d", "vitamin-e", "vitamin-k", "vitamin-c",
         "vitamin-b1", "vitamin-b2", "vitamin-pp", "vitamin-b6", "vitamin-b9", "vitamin-b12", "calcium", "iron", "magnesium", "potassium", "zinc", "added-sugars",
         "fruits-vegetables-legumes-estimate-from-ingredients", "fruits-vegetables-nuts-estimate-from-ingredients"]
TEXT = ["code", "product_name", "brands", "categories_tags", "countries_tags", "labels_tags", "quantity", "product_quantity", "ingredients_text", "ingredients_analysis_tags", "traces_tags",
        "allergens", "additives_tags", "serving_quantity", "nutriscore_grade", "nova_group", "last_modified_t", "image_small_url", "unique_scans_n"]


def tags(v):
    return [x for x in (v or "").split(",") if x]


def main(csv_path: str, out: str = OUT) -> None:
    t0 = time.time()
    tmp = out + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.executescript("""
      create table off_products (code text primary key, scans integer, data text);
      create table off_cat (tag text, code text, scans integer);
      create virtual table off_names using fts5(code unindexed, text, tokenize='unicode61 remove_diacritics 2');
    """)
    con = duckdb.connect()
    con.execute("pragma threads=4")
    header = con.execute(f"select * from read_csv('{csv_path}', delim='\\t', header=true, quote='', escape='', all_varchar=true, ignore_errors=true, sample_size=2000) limit 0").description
    have = {d[0] for d in header}
    cols = [c for c in TEXT + [n + "_100g" for n in NUTRI] if c in have]
    q = ", ".join(f'"{c}"' for c in cols)
    cur = con.execute(f"""select {q} from read_csv('{csv_path}', delim='\\t', header=true, quote='', escape='', all_varchar=true, ignore_errors=true, parallel=true)
                          where countries_tags like '%en:france%' and code is not null and product_name is not null and product_name <> ''""")
    idx = {c: i for i, c in enumerate(cols)}
    n = 0
    while True:
        rows = cur.fetchmany(5000)
        if not rows:
            break
        prod, cat, fts = [], [], []
        for r in rows:
            g = lambda c: r[idx[c]] if c in idx else None  # noqa: E731
            code = g("code")
            if not code or not re.fullmatch(r"\d{6,14}", code):
                continue
            nm = {f"{k}_100g": g(f"{k}_100g") for k in NUTRI if g(f"{k}_100g") not in (None, "")}
            fvn = nm.get("fruits-vegetables-legumes-estimate-from-ingredients_100g")
            raw = {"code": code, "product_name": g("product_name"), "brands": g("brands"), "categories_tags": tags(g("categories_tags")), "countries_tags": tags(g("countries_tags")),
                   "labels_tags": tags(g("labels_tags")), "quantity": g("quantity"), "product_quantity": g("product_quantity"), "ingredients_text": g("ingredients_text"),
                   "ingredients_analysis_tags": tags(g("ingredients_analysis_tags")), "traces_tags": tags(g("traces_tags")), "allergens_tags": tags(g("allergens")),
                   "additives_tags": tags(g("additives_tags")), "serving_quantity": g("serving_quantity"), "nutriscore_grade": g("nutriscore_grade"), "nova_group": g("nova_group"),
                   "last_modified_t": int(g("last_modified_t")) if (g("last_modified_t") or "").isdigit() else None, "image_front_small_url": g("image_small_url"), "nutriments": nm}
            scans = int(g("unique_scans_n")) if (g("unique_scans_n") or "").isdigit() else 0
            prod.append((code, scans, json.dumps(raw, separators=(",", ":"))))
            cat += [(t, code, scans) for t in raw["categories_tags"]]
            fts.append((code, f'{g("product_name")} {g("brands") or ""}'))
        db.executemany("insert or replace into off_products values (?,?,?)", prod)
        db.executemany("insert into off_cat values (?,?,?)", cat)
        db.executemany("insert into off_names values (?,?)", fts)
        n += len(prod)
        if n % 50000 < 5000:
            print(f"  {n:,} French products  ({time.time() - t0:0.0f}s)", flush=True)
    db.execute("create index off_cat_tag on off_cat (tag, scans desc)")
    db.commit()
    db.close()
    os.replace(tmp, out)  # atomic swap: the running app switches to the new copy on its next query
    print(f"done: {n:,} French products -> {out}  ({time.time() - t0:0.0f}s)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
