"""Which chains sell each popular brand, from evidence only: price observations (Open Prices and the retailer exports) joined to each product's brand.

    cd backend && .venv/bin/python -m scripts.build_brand_chains [N]      # N most popular brands (default 2000), writes brand_chains.json

Popularity = total Open Food Facts scan counts of the brand's French products. A chain is listed for a brand when at least MIN_PRODUCTS of its
products were seen there; "support" is how many. Brands sold by one chain only (store brands) come out with that single chain."""
import collections
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
OP = os.environ.get("OP_LOCAL", os.path.join(HERE, "op_local.db"))
OUT = os.environ.get("BRAND_CHAINS", os.path.join(HERE, "brand_chains.json"))
MIN_PRODUCTS = 2


def norm(b: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñ&' ]", " ", b.lower())).strip()


def main(top: int = 2000) -> None:
    from app import chains as ch
    off, op = sqlite3.connect(OFF), sqlite3.connect(OP)
    brand_of, pop = {}, collections.Counter()
    for code, scans, data in off.execute("select code, scans, data from off_products where scans > 0"):
        try:
            b = (json.loads(data).get("brands") or "").split(",")[0]
        except ValueError:
            continue
        b = norm(b)
        if b:
            brand_of[code] = b
            pop[b] += scans or 1
    ranked = [b for b, _ in pop.most_common(top)]
    keep = set(ranked)
    seen = collections.defaultdict(lambda: collections.defaultdict(set))      # brand -> chain -> product codes
    for code, data in op.execute("select code, data from op_items"):
        b = brand_of.get(code)
        if b not in keep:
            continue
        try:
            loc = json.loads(data).get("location") or {}
        except ValueError:
            continue
        chain = ch.canon(loc.get("osm_brand")) or ch.canon(loc.get("osm_name"))
        if chain:
            seen[b][chain].add(code)
    out = []
    for rank, b in enumerate(ranked, 1):
        cs = sorted(((c, len(v)) for c, v in seen[b].items() if len(v) >= MIN_PRODUCTS), key=lambda x: -x[1])
        out.append({"rank": rank, "brand": b, "scans": pop[b], "chains": [{"chain": c, "products": n} for c, n in cs]})
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_chain = sum(1 for r in out if r["chains"])
    print(f"{len(out)} brands, {with_chain} with at least one chain ({with_chain / max(1, len(out)):.0%}) -> {OUT}")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
