"""Type-by-type audit of the taxonomy index (off_taxo, built by scripts/build_taxonomy_index.py).

For each product type: how many products, how many look unsupported (the product name shares no word with the type's name or
aliases, so it was placed by a tag or a loose rule only), and examples of both kinds. Types are ranked by suspicious share.

    cd backend && .venv/bin/python -m scripts.audit_types [--min 8] [--top 40] [--only P0123,P0456] [--out report.txt]
"""
import argparse, collections, json, os, re, sqlite3, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from app import taxorules as T  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--min", type=int, default=8)
ap.add_argument("--n", type=int, default=40000)
ap.add_argument("--min-scans", type=int, default=0)
ap.add_argument("--top", type=int, default=40)
ap.add_argument("--per", type=int, default=4)
ap.add_argument("--only", default="")
ap.add_argument("--out", default="")
a = ap.parse_args()
N = T.load()["nodes"]
STOP = {"de", "du", "des", "la", "le", "les", "en", "et", "au", "aux", "a", "d", "l", "non", "precise", "precises", "divers", "autres", "ou", "sans", "avec", "pour", "sur"}
def stem(w): return re.sub(r"(s|x|e|es)$", "", w) if len(w) > 4 else w
def toks(s): return {stem(w) for w in T.norm(s).split() if w not in STOP and len(w) > 2}
db = sqlite3.connect(os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db")))
want = set(a.only.split(",")) if a.only else None
rows = collections.defaultdict(list)
names = {}
from app import taxo1000  # noqa: E402
for code, data in db.execute(f"select code, data from off_products where scans >= {a.min_scans} order by random() limit {a.n}"):
    r = json.loads(data)
    nm = r.get("product_name") or ""
    if not nm.strip():
        continue
    cl = taxo1000.classify(nm, r.get("generic_name"), r.get("brands"), r.get("categories_tags"))
    if cl.get("level") == 3 and cl.get("type") and (want is None or cl["type"] in want):
        rows[cl["type"]].append((code, cl.get("source")))
        names[code] = nm
rep = []
for typ, lst in rows.items():
    if len(lst) < a.min:
        continue
    node = N[typ]
    key = toks(node["name_fr"]) | toks(node.get("name_en") or "")
    sample = lst[:400] if len(lst) > 400 else lst
    bad, good = [], []
    for code, src in sample:
        name = names[code]
        (good if (toks(name) & key) else bad).append(name[:60])
    share = len(bad) / max(1, len(bad) + len(good))
    rep.append((share, len(lst), typ, node["name_fr"], bad[:a.per], good[:2]))
rep.sort(key=lambda x: (-x[0] * (min(x[1], 200) ** 0.5), -x[1]))
out = [f"{len(rep)} types with >= {a.min} products. Most suspicious first (share of sampled products whose name shares no word with the type):", ""]
for share, n, typ, nm, bad, good in rep[:a.top]:
    out.append(f"{typ} {nm}  [{N[typ]['path_fr']}]  n={n}  unsupported={share:.0%}")
    for b in bad: out.append(f"     ? {b}")
    for g in good: out.append(f"     ok {g}")
txt = "\n".join(out)
if a.out: open(a.out, "w").write(txt)
print(txt)
