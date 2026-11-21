"""Audit the alternatives of every specific Mieux type.

For each product type that has a priced product in alt_index.db, scan its most-scanned priced product through the real
alternatives endpoint and look at the top 100 alternatives (value ranking; the match list when there is no price ranking).
Each alternative is placed with the taxonomy index (off_taxo): how many are the same type, the same category, another
department? Types whose alternatives drift out of the category are the ones to fix.

    cd backend && .venv/bin/python -m scripts.audit_alternatives [--workers 4] [--limit 0] [--out alt_audit.jsonl]
    cd backend && .venv/bin/python -m scripts.audit_alternatives --report alt_audit.jsonl [--top 40]
"""
import argparse, collections, json, multiprocessing as mp, os, sqlite3, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
ALT = os.environ.get("ALT_INDEX", os.path.join(HERE, "alt_index.db"))
PAYLOAD = {"priorities": ["protein"], "profile": "balanced"}


def reps(limit):
    db = sqlite3.connect(OFF)
    db.execute("attach database ? as a", (f"file:{ALT}?mode=ro",))
    rows = db.execute("""select t.type, t.code, al.scans from off_taxo t join a.alt al on al.code = t.code
                         where t.level = 3 and t.type is not null order by al.scans desc""").fetchall()
    best = {}
    for typ, code, scans in rows:
        best.setdefault(typ, code)
    out = sorted(best.items())
    return out[:limit] if limit else out


def work(args):
    wid, items = args
    os.environ["DATABASE_URL"] = f"sqlite:////private/tmp/audit_app_{wid}.db"
    os.environ.setdefault("JWT_SECRET_KEY", "audit")
    if os.path.exists(f"/private/tmp/audit_app_{wid}.db"):
        os.remove(f"/private/tmp/audit_app_{wid}.db")
    sys.path.insert(0, HERE)
    from fastapi.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    off = sqlite3.connect(OFF)
    H = {"X-Session-Id": f"audit-session-{wid:04d}", "X-Country": "FR"}
    res = []
    for typ, code in items:
        o = off.execute("select type, category, department from off_taxo where code=?", (code,)).fetchone()
        try:
            r = c.post(f"/v1/products/{code}/alternatives", json=PAYLOAD, headers=H)
            j = r.json()
        except Exception as e:  # noqa: BLE001
            res.append({"type": typ, "code": code, "error": str(e)[:100]})
            continue
        if r.status_code != 200:
            res.append({"type": typ, "code": code, "error": f"http {r.status_code}"})
            continue
        rk = j.get("rankings") or {}
        lst = rk.get("value") or rk.get("match") or j.get("alternatives") or []
        source = "value" if rk.get("value") else "match"
        same_t = same_c = same_d = 0
        off_examples = []
        for it in lst[:100]:
            bc = (it.get("product") or {}).get("barcode")
            x = off.execute("select type, category, department from off_taxo where code=?", (bc,)).fetchone()
            if not x:
                continue
            same_t += x[0] == o[0]
            same_c += x[1] == o[1]
            same_d += x[2] == o[2]
            if x[1] != o[1] and len(off_examples) < 6:
                off_examples.append([(it.get("product") or {}).get("name", "")[:50], x[0]])
        n = len(lst[:100])
        res.append({"type": typ, "code": code, "orig": (j.get("original") or {}).get("name"), "orig_cat": o[1], "n": n, "source": source,
                    "same_type": same_t, "same_cat": same_c, "same_dept": same_d, "off": off_examples, "already_great": bool(j.get("already_great"))})
    return res


def report(path, top):
    sys.path.insert(0, HERE)
    from app import taxorules
    N = taxorules.load()["nodes"]
    rows = [json.loads(l) for l in open(path)]
    ok = [r for r in rows if "error" not in r and r["n"] > 0]
    print(f"{len(rows)} types audited, {len(ok)} with alternatives, {sum(1 for r in rows if 'error' in r)} errors, {sum(1 for r in rows if r.get('n') == 0)} with none")
    if ok:
        tot = sum(r["n"] for r in ok)
        print(f"overall over {tot} alternatives: same type {100 * sum(r['same_type'] for r in ok) / tot:.1f}%, same category {100 * sum(r['same_cat'] for r in ok) / tot:.1f}%, same department {100 * sum(r['same_dept'] for r in ok) / tot:.1f}%")
    bad = sorted(ok, key=lambda r: (r["same_cat"] / r["n"], r["same_type"] / r["n"]))
    print(f"\nworst {top} types by share of alternatives in the same category:")
    for r in bad[:top]:
        print(f"  cat {100 * r['same_cat'] / r['n']:3.0f}% type {100 * r['same_type'] / r['n']:3.0f}% (n={r['n']}, {r['source']})  {N[r['type']]['name_fr']}  <- {str(r['orig'])[:40]}")
        for nm, t in r["off"][:3]:
            print(f"        off-category: {nm} [{N[t]['name_fr'] if t in N else t}]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "alt_audit.jsonl"))
    ap.add_argument("--report", default="")
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    if a.report:
        report(a.report, a.top)
        sys.exit()
    items = reps(a.limit)
    print(len(items), "types to audit", flush=True)
    chunks = [(i, items[i::a.workers]) for i in range(a.workers)]
    t0 = time.time()
    with open(a.out, "w") as fh, mp.Pool(a.workers) as pool:
        for res in pool.imap_unordered(work, chunks):
            for r in res:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
    print(f"done in {time.time() - t0:.0f} s -> {a.out}")
