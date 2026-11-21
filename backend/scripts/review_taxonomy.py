"""Category-by-category review: for one department (or category) print how many products land in each type and a few
example names for each, so a human can eyeball whether the placement is right.

    cd backend && .venv/bin/python -m scripts.review_taxonomy D_16 [--n 60000] [--per 4] [--only-bad]
"""
import argparse, collections, json, os, sqlite3, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from app import taxorules as T  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("prefix")
ap.add_argument("--n", type=int, default=60000)
ap.add_argument("--per", type=int, default=4)
ap.add_argument("--top", type=int, default=30)
a = ap.parse_args()
L = T.load(); N = L["nodes"]
db = sqlite3.connect(os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db")))
by = collections.defaultdict(list)
for (d,) in db.execute(f"select data from off_products order by random() limit {a.n}"):
    r = json.loads(d); nm = r.get("product_name") or ""
    if not nm.strip():
        continue
    m = T.match(nm, r.get("generic_name"), r.get("categories_tags"))
    if m:
        nid = m["type"] or m["category"] or m["department"]
        if (m["category"] or m["department"] or "").startswith("C_" + a.prefix.replace("D_", "")) or (m["department"] or "").startswith(a.prefix):
            by[nid].append((nm, m["source"]))
for nid, v in sorted(by.items(), key=lambda kv: -len(kv[1]))[:a.top]:
    print(f"{len(v):5}  {N[nid]['name_fr']}  [{N[nid]['path_fr']}]")
    for nm, src in v[:a.per]:
        print(f"         {src[0]} {nm[:70]}")
