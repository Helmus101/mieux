"""Make a hand-check sheet for the taxonomy: a stratified random sample of products people actually scan, with the type the
classifier chose. A human fills `correct` (y/n) and, when n, `right_type` (any wording); score_taxonomy_sheet.py turns it into
accuracy per department.

    cd backend && .venv/bin/python -m scripts.make_taxonomy_sheet [--n 600] [--out taxonomy_sheet.csv]
"""
import argparse, collections, csv, json, os, random, sqlite3, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from app import taxo1000, taxorules  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=600)
ap.add_argument("--pool", type=int, default=30000)
ap.add_argument("--out", default=os.path.join(HERE, "taxonomy_sheet.csv"))
a = ap.parse_args()
N = taxorules.load()["nodes"]
db = sqlite3.connect(os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db")))
by = collections.defaultdict(list)
for code, data in db.execute(f"select code, data from off_products where scans >= 2 order by random() limit {a.pool}"):
    r = json.loads(data)
    nm = (r.get("product_name") or "").strip()
    if not nm:
        continue
    cl = taxo1000.classify(nm, r.get("generic_name"), r.get("brands"), r.get("categories_tags"))
    dep = cl.get("department") or "UNCLASSIFIED"
    by[dep].append((code, nm, r.get("brands") or "", cl))
random.seed(7)
per = max(5, a.n // max(1, len(by)))
rows = []
for dep, lst in sorted(by.items()):
    for code, nm, br, cl in random.sample(lst, min(per, len(lst))):
        nid = cl.get("type") or cl.get("category") or cl.get("department")
        rows.append({"code": code, "name": nm, "brand": br, "department": N[dep]["name_fr"] if dep in N else dep,
                     "level": cl.get("level", 0), "chosen": N[nid]["path_fr"] if nid else "", "source": cl.get("source") or "", "correct": "", "right_type": ""})
with open(a.out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows ->", a.out)
