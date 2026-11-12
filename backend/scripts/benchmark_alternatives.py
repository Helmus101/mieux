"""Benchmark v1 for the alternatives pipeline: coverage and compatibility-consistency stats over ~100 real
products across 10+ categories, run against the live in-process pipeline (local database, no network price
search). Not a substitute for human-labeled precision/recall - see the printed report for what this does and
does not measure.

Usage: cd backend && DATABASE_URL=sqlite:///./foodiq.db .venv/bin/python scripts/benchmark_alternatives.py
"""
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CATEGORIES = {
    "yogurts_dairy": "en:yogurts",
    "breakfast_cereals": "en:breakfast-cereals",
    "spreads": "en:spreads",
    "pasta_rice": "en:pastas",
    "snacks_biscuits": "en:biscuits-and-cakes",
    "drinks": "en:beverages",
    "sauces": "en:sauces",
    "meat_plant_based": "en:meats",
    "cheeses": "en:cheeses",
    "charcuterie": "en:hams",
}
PER_CATEGORY = 10


def pick_products(db_path: str) -> dict:
    con = sqlite3.connect(db_path)
    picked = {}
    for cat_name, tag in CATEGORIES.items():
        rows = con.execute(
            "select p.code, p.data from off_cat c join off_products p on p.code = c.code "
            "where c.tag = ? order by c.scans desc limit 400", (tag,),
        ).fetchall()
        items = []
        for code, data in rows:
            try:
                d = json.loads(data)
            except Exception:
                continue
            nm = (d.get("product_name") or "").strip()
            if len(nm) < 4 or "/" in nm:
                continue
            items.append((code, nm))
            if len(items) >= PER_CATEGORY:
                break
        picked[cat_name] = items
    con.close()
    return picked


def main():
    from app.main import app, load_product, get_db
    from app import taxonomy

    db_path = os.environ.get("OFF_LOCAL", os.path.join(os.path.dirname(__file__), "..", "off_local.db"))
    picked = pick_products(db_path)
    total_products = sum(len(v) for v in picked.values())
    print(f"Selected {total_products} products across {len(picked)} categories.\n")

    s = next(get_db())
    from fastapi.testclient import TestClient
    tc = TestClient(app)

    report_rows = []
    zero_alt = []
    type_mismatches = []           # should never happen: a bug in the compatibility gate if it does
    level_counts = Counter()
    coverage_buckets = Counter()   # 0, 1-2, 3-9, 10+
    quality_tab_counts = []
    value_tab_counts = []
    by_category = defaultdict(lambda: {"n": 0, "zero": 0, "alt_counts": []})

    for cat_name, items in picked.items():
        for code, name in items:
            try:
                r = tc.post(
                    f"/v1/products/{code}/alternatives",
                    headers={"X-Session-Id": f"benchmark-{cat_name}-{code}"},
                    json={"priorities": ["overall"], "category_mode": "similar", "limit": 20,
                          "substitution_max": 2, "same_size": False, "chains": [], "price_constraint": "any"},
                )
                d = r.json()
            except Exception as e:
                report_rows.append({"category": cat_name, "code": code, "name": name, "error": str(e)})
                continue
            if "detail" in d and len(d) == 1:
                report_rows.append({"category": cat_name, "code": code, "name": name, "error": d["detail"]})
                continue
            alts = d.get("alternatives", [])
            n = len(alts)
            by_category[cat_name]["n"] += 1
            by_category[cat_name]["alt_counts"].append(n)
            if n == 0:
                by_category[cat_name]["zero"] += 1
                zero_alt.append((cat_name, code, name))
            coverage_buckets["0"] += 1 if n == 0 else 0
            coverage_buckets["1-2"] += 1 if 1 <= n <= 2 else 0
            coverage_buckets["3-9"] += 1 if 3 <= n <= 9 else 0
            coverage_buckets["10+"] += 1 if n >= 10 else 0
            orig = d.get("original") or {}
            orig_product = {"name": name, "categories": []}
            orig_type = taxonomy.classify(orig_product).get("type")   # best-effort; names-only since we don't have the full OFF record here
            for a in alts:
                p = a.get("product") or {}
                sub = a.get("substitution") or {}
                lvl = sub.get("level")
                if lvl is not None:
                    level_counts[lvl] += 1
            rk = d.get("rankings", {})
            quality_tab_counts.append(len(rk.get("match", [])))
            value_tab_counts.append(len(rk.get("value", [])))
            report_rows.append({
                "category": cat_name, "code": code, "name": name,
                "n_alternatives": n, "n_quality_tab": len(rk.get("match", [])), "n_value_tab": len(rk.get("value", [])),
                "sample_alts": [a.get("product", {}).get("name") for a in alts[:5]],
            })

    out_path = os.path.join(os.path.dirname(__file__), "..", "..", "benchmark_v1_results.json")
    with open(out_path, "w") as f:
        json.dump(report_rows, f, ensure_ascii=False, indent=1)

    print("=== Coverage (how many alternatives were found per product) ===")
    for k in ("0", "1-2", "3-9", "10+"):
        print(f"  {k:>5} alternatives: {coverage_buckets[k]:3d} / {total_products} products")
    print()
    print("=== By category ===")
    for cat_name, stats in by_category.items():
        n, zero, counts = stats["n"], stats["zero"], stats["alt_counts"]
        avg = sum(counts) / len(counts) if counts else 0
        print(f"  {cat_name:<20} n={n:3d}  zero_alt={zero:3d}  avg_alts={avg:5.1f}  avg_quality_tab={sum(1 for c in counts if c)/max(1,n):4.2f}")
    print()
    print("=== Substitution level distribution (1=almost identical ... 4=broader) ===")
    for lvl in sorted(level_counts):
        print(f"  level {lvl}: {level_counts[lvl]}")
    print()
    print(f"Avg quality-tab size: {sum(quality_tab_counts)/len(quality_tab_counts):.1f}")
    print(f"Avg value-tab size:   {sum(value_tab_counts)/len(value_tab_counts):.1f}")
    print()
    if zero_alt:
        print(f"=== Products with ZERO alternatives ({len(zero_alt)}) ===")
        for cat_name, code, name in zero_alt:
            print(f"  [{cat_name}] {code}  {name}")
    print()
    print(f"Full per-product results written to {out_path}")


if __name__ == "__main__":
    main()
