"""Builds the sheet humans label: real French products (barcodes from the local Open Food Facts copy), each with the alternatives
Mieux shows today plus hard negatives (same OFF category tag family but a different Mieux type), label left empty.

    cd backend && .venv/bin/python3.9 scripts/make_labeling_sheet.py --types 50 --per-type 10 --out ../data/ground_truth/to_label.jsonl

Labellers fill "label" with valid | invalid | conditional for every candidate and "note" for the hard ones; two people label the
same rows independently, disagreements are settled in a third pass. Then run scripts/evaluate_ground_truth.py on the result.
Keep labelled rows OUT of the data used to tune taxonomy.py (tune on one half, report on the other)."""
import argparse, json, os, random, sqlite3, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for k in ("DEEPSEEK_API_KEY", "GEMINI_API_KEY", "SERPER_API_KEY", "LANGSEARCH_API_KEY", "PARALLEL_API_KEY", "BRAVE_API_KEY", "SUPABASE_URL"):
    os.environ[k] = ""
os.environ.setdefault("DATABASE_URL", "sqlite:///./sheet.db")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 40)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", type=int, default=50); ap.add_argument("--per-type", type=int, default=10)
    ap.add_argument("--hard-negatives", type=int, default=3); ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    from fastapi.testclient import TestClient
    from app.main import app
    from app import taxonomy
    from app.products import normalize
    rnd = random.Random(a.seed)
    con = sqlite3.connect(os.environ.get("OFF_LOCAL", "off_local.db"))
    types = [r[0] for r in con.execute("select type from off_type where type not like 'cat:%' group by type having count(*) >= 300 order by count(*) desc")]
    rnd.shuffle(types); types = types[:a.types]
    rows = 0
    with TestClient(app) as c, open(a.out, "w") as out:
        H = {"X-Session-Id": "labelling-sheet-000001", "X-Country": "FR"}
        for t in types:
            codes = [r[0] for r in con.execute("select code from off_type where type=? and code glob '[0-9]*' and length(code)>=8 and confidence in ('high','medium') order by scans desc limit 200", (t,))]
            for code in rnd.sample(codes, min(a.per_type, len(codes))):
                d = c.post(f"/v1/products/{code}/alternatives", headers=H, json={"priorities": ["protein"]}).json()
                orig = d.get("original") or {}
                cands, seen = [], set()
                for k in ("value", "match"):
                    for e in ((d.get("rankings") or {}).get(k) or [])[:5]:
                        p = e.get("product") or {}
                        if p.get("barcode") and p["barcode"] not in seen:
                            seen.add(p["barcode"]); cands.append({"barcode": p["barcode"], "name": p.get("name"), "brand": p.get("brand"), "source": "mieux", "label": None, "note": ""})
                neg = [r for r in con.execute("select o.code from off_type t join off_products o using(code) where t.type<>? and t.type not like 'cat:%' and t.code glob '[0-9]*' order by random() limit 400", (t,))]
                tags = set(orig.get("categories") or [])
                added = 0
                for (nc,) in neg:
                    if added >= a.hard_negatives: break
                    raw = con.execute("select data from off_products where code=?", (nc,)).fetchone()
                    if not raw: continue
                    p = normalize(json.loads(raw[0]))
                    if tags & set(p.get("categories") or []) and nc not in seen:
                        seen.add(nc); added += 1
                        cands.append({"barcode": nc, "name": p.get("name"), "brand": p.get("brand"), "source": "hard_negative", "label": None, "note": ""})
                out.write(json.dumps({"original": {"barcode": code, "name": orig.get("name"), "brand": orig.get("brand"), "categories": (orig.get("categories") or [])[-4:]}, "candidates": cands}, ensure_ascii=False) + "\n")
                rows += 1
    print("originals written:", rows, "->", a.out)


if __name__ == "__main__":
    main()
