"""Build off_quick.db: one compact row per product (Nutri-Score and the six numbers alternatives are ranked on).

Scanning a category by reading and parsing every product record costs about 0.2 ms per product, so a category of 9 000
products cannot be looked at in full on each request. This side table makes the same choice in SQL in a few milliseconds,
which lets the API consider a whole category instead of its most scanned page.

Run it after importing a new Open Food Facts dump (scripts/import_off_dump.py). The API keeps working without it: it then
falls back to reading the most scanned products of each category.

    cd backend && . .venv/bin/activate && python scripts/build_quick_index.py
"""
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
DST = os.environ.get("OFF_QUICK", os.path.join(HERE, "off_quick.db"))
BATCH = 5000


def num(nm, *keys):
    """First of these per-100 g values, as a float; None when absent (never zero)."""
    for k in keys:
        v = nm.get(k + "_100g")
        if v in (None, ""):
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return None


def main() -> None:
    if not os.path.exists(SRC):
        sys.exit(f"no Open Food Facts copy at {SRC}")
    src = sqlite3.connect(f"file:{SRC}?mode=ro", uri=True)
    dst = sqlite3.connect(DST)
    dst.execute("pragma journal_mode=wal")
    dst.execute("create table if not exists quick (code text primary key, grade text, sugar real, salt real, "
                "protein real, fibre real, sat real, kcal real, ing int) without rowid")
    t0, n, written = time.time(), 0, 0
    buf = []

    def flush() -> None:
        nonlocal buf, written
        if not buf:
            return
        dst.executemany("insert or replace into quick values (?,?,?,?,?,?,?,?,?)", buf)
        dst.commit()
        written += len(buf)
        buf = []

    for code, data in src.execute("select code, data from off_products"):
        n += 1
        try:
            r = json.loads(data)
        except ValueError:
            continue
        nm = r.get("nutriments") or {}
        salt = num(nm, "salt")
        if salt is None:
            sodium = num(nm, "sodium")
            salt = None if sodium is None else sodium * 2.5
        grade = (r.get("nutriscore_grade") or "").strip().lower() or None
        buf.append((code, grade if grade in ("a", "b", "c", "d", "e") else None,
                    num(nm, "sugars"), salt, num(nm, "proteins"), num(nm, "fiber"), num(nm, "saturated-fat"),
                    num(nm, "energy-kcal"), 1 if r.get("ingredients_text") else 0))
        if len(buf) >= BATCH:
            flush()
            print(f"  {n} read, {written} indexed ({time.time() - t0:.0f} s)", flush=True)
    flush()
    dst.execute("create index if not exists quick_sugar on quick(sugar)")
    dst.execute("create index if not exists quick_salt on quick(salt)")
    dst.execute("create index if not exists quick_protein on quick(protein)")
    dst.execute("create index if not exists quick_fibre on quick(fibre)")
    dst.commit()
    print(f"done: {written} products indexed from {n} read, in {time.time() - t0:.0f} s -> {DST}")


if __name__ == "__main__":
    main()
