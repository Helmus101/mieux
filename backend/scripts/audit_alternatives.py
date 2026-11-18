"""Audit alternatives for the most-scanned products: runs the real /alternatives endpoint in-process (web price search off, no
network) and prints, per product type, the originals and the alternatives they got, so wrong pools stand out by name.

    cd backend && .venv/bin/python scripts/audit_alternatives.py 1000 /tmp/audit.json
    cd backend && .venv/bin/python scripts/audit_alternatives.py --review /tmp/audit.json
"""
import collections, json, sys


def review(path):
    res = json.load(open(path))
    by = collections.defaultdict(lambda: {"orig": [], "alts": collections.Counter(), "empty": 0})
    errs = [r for r in res if r.get("err") or r.get("status") != 200]
    for r in res:
        if r.get("err"): continue
        g = by[r["t"]]
        g["orig"].append((r.get("n") or "")[:30])
        if not r["alts"]: g["empty"] += 1
        for a in r["alts"]:
            g["alts"][(a["n"][:34], a["t"] if a["t"] != r["t"] else "=")] += 1
    print("products", len(res), "errors", len(errs), "types", len(by), "empty", sum(g["empty"] for g in by.values()))
    for t, g in sorted(by.items(), key=lambda kv: -len(kv[1]["orig"])):
        print(f"\n## {t}  n={len(g['orig'])} empty={g['empty']}  e.g. {g['orig'][:4]}")
        print("   ", " · ".join(f"{n}{'' if tt == '=' else ' ['+str(tt)+']'}" for (n, tt), c in g["alts"].most_common(14)))


def run(n, out, offset=0):
    import os, sys, json, time, sqlite3
    sys.path.insert(0, '.')
    for k in ("DEEPSEEK_API_KEY","GEMINI_API_KEY","SERPER_API_KEY","LANGSEARCH_API_KEY","PARALLEL_API_KEY","BRAVE_API_KEY","SUPABASE_URL"):
        os.environ[k] = ""
    os.environ.setdefault("DATABASE_URL", "sqlite:///./audit.db")
    os.environ.setdefault("JWT_SECRET_KEY", "x"*40)
    N, OUT, OFFSET = int(n), out, int(offset)
    from fastapi.testclient import TestClient
    from app.main import app
    from app import taxonomy
    from app.products import normalize
    con = sqlite3.connect('off_local.db')
    codes = [r[0] for r in con.execute("select code from off_products where code glob '[0-9]*' and length(code)>=8 order by scans desc limit ? offset ?", (N, OFFSET))]
    out = []
    with TestClient(app) as c:
        H = {"X-Session-Id": "audit-session-000001", "X-Country": "FR"}
        t0 = time.time()
        for i, b in enumerate(codes):
            try:
                r = c.post(f"/v1/products/{b}/alternatives", headers=H, json={"priorities": ["protein"]})
                d = r.json()
            except Exception as e:
                out.append({"b": b, "err": repr(e)[:100]}); continue
            o = None
            try:
                raw = json.loads(con.execute("select data from off_products where code=?", (b,)).fetchone()[0])
                o = normalize(raw)
            except Exception:
                pass
            ot = taxonomy.classify(o).get("type") if o else None
            alts = []
            seen = set()
            for k in ("value", "match"):
                for e in ((d.get("rankings") or {}).get(k) or [])[:5]:
                    p = e.get("product") or {}
                    if p.get("barcode") in seen: continue
                    seen.add(p.get("barcode"))
                    alts.append({"k": k, "b": p.get("barcode"), "n": (p.get("name") or "")[:60], "t": taxonomy.classify(p).get("type"), "lvl": (e.get("substitution") or {}).get("level")})
            out.append({"b": b, "n": (o or {}).get("name"), "t": ot, "status": r.status_code, "alts": alts, "reason": d.get("no_recommendation_reason")})
            if i % 50 == 0:
                print(i, round(time.time()-t0), flush=True)
                json.dump(out, open(OUT, "w"))
    json.dump(out, open(OUT, "w"))
    print("done", len(out))


if __name__ == '__main__':
    if sys.argv[1] == '--review':
        review(sys.argv[2])
    else:
        run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 0)
