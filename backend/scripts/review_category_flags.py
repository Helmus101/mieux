"""List the "wrong category" flags people sent, most-flagged products first, as golden-test candidates.

    cd backend && DATABASE_URL=... .venv/bin/python -m scripts.review_category_flags [--limit 50]

For each product: the name, the type it was placed at, the type the person suggested (if any) and how many people flagged it. Fix the rule in
app/data/taxo_rules.txt, then add the product name and its right type to tests/data/taxonomy_golden.json.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import func  # noqa: E402
from app import db, taxo1000  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=50); a = ap.parse_args()
    s = db.make_session_factory()()
    names = {}
    def nm(t):
        if t not in names:
            names[t] = (taxo1000.node(t) or {}).get("name_fr") if t else None
        return names[t]
    rows = (s.query(db.CategoryFlag.product_id, db.CategoryFlag.name, db.CategoryFlag.placed_type, db.CategoryFlag.suggested_type, func.count())
            .group_by(db.CategoryFlag.product_id, db.CategoryFlag.name, db.CategoryFlag.placed_type, db.CategoryFlag.suggested_type)
            .order_by(func.count().desc()).limit(a.limit).all())
    for pid, name, placed, sugg, n in rows:
        print(json.dumps({"flags": n, "product": pid, "name": name, "placed": [placed, nm(placed)], "suggested": [sugg, nm(sugg)]}, ensure_ascii=False))
    print(f"{len(rows)} flagged products")


if __name__ == "__main__":
    main()
