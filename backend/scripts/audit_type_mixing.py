"""Finds Mieux types that mix products shoppers see as different things (raisins and prunes under one "dried fruit").

For every type, the products people actually scan are grouped by their most specific Open Food Facts category tag. A type whose
products split into several large groups, and that has no variant rules telling them apart, is a candidate for variants
(app/taxonomy.py _VARIANTS and _HARD_VARIANT_TYPES). Read-only: it only reads off_local.db.

    cd backend && .venv/bin/python3.9 scripts/audit_type_mixing.py [--min-scans 3] [--min-products 200] [--top 40]
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app import taxonomy  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def leaf(tags):
    """The most specific tag that is not a generic shelf: OFF lists tags from general to specific."""
    for t in reversed(tags or []):
        if t not in taxonomy._GENERIC_LEAF and t not in taxonomy._BROAD_LEAFS:
            return t
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db")))
    ap.add_argument("--min-scans", type=int, default=3)
    ap.add_argument("--min-products", type=int, default=200)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    groups = defaultdict(Counter)
    rows = db.execute("select t.type, p.data from off_type t join off_products p on p.code = t.code where p.scans >= ?", (a.min_scans,))
    for typ, data in rows:
        if not typ or typ.startswith("cat:"):
            continue
        try:
            d = json.loads(data)
        except ValueError:
            continue
        lf = leaf(d.get("categories_tags"))
        if lf:
            groups[typ][lf] += 1
    report = []
    for typ, c in groups.items():
        n = sum(c.values())
        if n < a.min_products:
            continue
        top = c.most_common(4)
        big = [(k, v) for k, v in top if v / n >= 0.08]
        has_variants = typ in taxonomy._VARIANTS
        # "mixed": at least three leaves each holding 8% or more, i.e. no single kind dominates
        if len(big) >= 3 and top[0][1] / n < 0.6:
            report.append((n, typ, has_variants, typ in taxonomy._HARD_VARIANT_TYPES, big))
    report.sort(key=lambda r: -r[0])
    print(f"{'type':26}{'n':>7}  variants  hard   largest groups (share)")
    for n, typ, hv, hard, big in report[: a.top]:
        print(f"{typ:26}{n:>7}  {'yes' if hv else 'NO ':8}  {'yes' if hard else 'no':4}   " + ", ".join(f"{k.split(':')[-1]} {v / n:.0%}" for k, v in big))
    missing = [r for r in report if not r[2]]
    print(f"\n{len(report)} mixed types, {len(missing)} without variant rules")


if __name__ == "__main__":
    main()
