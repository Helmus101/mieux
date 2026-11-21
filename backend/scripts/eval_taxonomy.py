"""Evaluate the rule classifier on a sample of the local OFF copy.

    cd backend && .venv/bin/python -m scripts.eval_taxonomy [--n 20000] [--show 40] [--dept D_16]

Reports coverage by level (3 = specific type, 2 = category, 1 = department, 0 = unclassified) and, for products that have OFF tags,
how often the name-only and tag-only verdicts agree. Disagreements are the best pointer to a misfiring rule."""
import argparse
import collections
import json
import os
import random
import sqlite3
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from app import taxorules as T  # noqa: E402

OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))


def name_of(nodes, r):
    if not r:
        return None
    return nodes[r["type"] or r["category"] or r["department"]]["name_fr"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--show", type=int, default=30)
    ap.add_argument("--dept", default="")
    ap.add_argument("--scanned", action="store_true", help="only products with scans >= 1 (the ones people meet)")
    a = ap.parse_args()
    L = T.load()
    nodes = L["nodes"]
    db = sqlite3.connect(OFF)
    where = "where scans>=1" if a.scanned else ""
    rows = db.execute(f"select data from off_products {where}").fetchall() if False else db.execute(f"select data from off_products {where} order by random() limit {a.n}").fetchall()
    lvl = collections.Counter()
    agree = collections.Counter()
    bad = collections.defaultdict(list)
    unc = []
    for (data,) in rows:
        r = json.loads(data)
        name = r.get("product_name") or ""
        if not name.strip():
            continue
        tags = r.get("categories_tags") or []
        both = T.match(name, r.get("generic_name"), tags)
        lvl[both["level"] if both else 0] += 1
        if not both:
            unc.append((name, tags[-2:]))
        if tags:
            n1 = T.match(name, r.get("generic_name"), None)
            t1 = T.match(None, None, tags)
            if n1 and t1:
                same_t = n1["type"] == t1["type"]
                same_d = n1["department"] == t1["department"]
                agree["both"] += 1
                agree["same_type"] += same_t
                agree["same_dept"] += same_d
                if not same_d:
                    bad[(name_of(nodes, n1), name_of(nodes, t1))].append(name)
    tot = sum(lvl.values())
    print(f"sampled {tot}: " + ", ".join(f"level {k}: {100 * v / tot:.1f}%" for k, v in sorted(lvl.items(), reverse=True)))
    if agree["both"]:
        print(f"name vs tag verdict ({agree['both']} products where both fire): same type {100 * agree['same_type'] / agree['both']:.1f}%, same department {100 * agree['same_dept'] / agree['both']:.1f}%")
    print("\nmost frequent department disagreements (name verdict -> tag verdict):")
    for (x, y), v in sorted(bad.items(), key=lambda kv: -len(kv[1]))[:a.show]:
        print(f"  {len(v):4}  {x}  ->  {y}   e.g. {v[0][:50]} | {v[1][:50] if len(v) > 1 else ''}")
    random.seed(1)
    print("\nunclassified examples:")
    for nm, tg in random.sample(unc, min(a.show, len(unc))):
        print("  ", nm[:55], tg)


if __name__ == "__main__":
    main()
