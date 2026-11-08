"""Reference distributions for the price-quality score: per product type, the spread of Mieux nutrition scores and of unit prices (cents per 100 g/ml).

    cd backend && .venv/bin/python -m scripts.build_value_reference        # writes value_reference.json

A product's price-quality score is read against these FIXED distributions (not against whatever candidates a search happened to return), so it
stays the same whatever the result limit. Only prices from the last 365 days, not estimates, with a known pack size, count."""
import collections
import json
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OUT = os.environ.get("VALUE_REFERENCE", os.path.join(HERE, "value_reference.json"))
VERSION = 1
QUANTILES = 41


def quantiles(xs, n=QUANTILES):
    xs = sorted(xs)
    return [round(xs[min(len(xs) - 1, int(i * (len(xs) - 1) / (n - 1) + 0.5))], 2) for i in range(n)]


def main() -> None:
    from app import taxonomy, value
    from app.products import normalize
    t0 = time.time()
    op = sqlite3.connect(os.path.join(HERE, "op_local.db"))
    off = sqlite3.connect(os.path.join(HERE, "off_local.db"))
    prices = value.OpenPricesClient(local_path=os.path.join(HERE, "op_local.db"))
    codes = [r[0] for r in op.execute("select distinct code from op_items")]
    by = collections.defaultdict(list)
    for code in codes:
        r = off.execute("select data from off_products where code=?", (code,)).fetchone()
        if not r:
            continue
        raw = json.loads(r[0]); raw["code"] = code
        p = normalize(raw)
        sc, q = (p.get("score") or {}).get("total"), p.get("quantity")
        if sc is None or not q:
            continue
        cl = taxonomy.classify(p)
        if not cl["type"] or cl["confidence"] in ("none", "low"):
            continue
        hit = prices.latest(code, (q["amount"], q["unit"]))
        if not hit or hit.get("stale") or hit.get("source") == "estimate" or not hit.get("per100_cents"):
            continue
        by[cl["type"]].append((sc, hit["per100_cents"]))
    types = {}
    for tid, rows in by.items():
        if len(rows) >= 15:
            types[tid] = {"n": len(rows), "score_q": quantiles([a for a, _ in rows]), "price_q": quantiles([b for _, b in rows])}
    json.dump({"version": VERSION, "built": time.strftime("%Y-%m-%d"), "types": types}, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(types)} types with >= 15 priced products ({sum(v['n'] for v in types.values()):,} products), {len(by) - len(types)} types too thin; {time.time() - t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
