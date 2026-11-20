"""Scores taxonomy.substitution() against tests/data/reference_pairs.json (labels written from shopper logic, not from the taxonomy).
A pair is predicted "valid" when substitution() returns level 1 or 2 (the levels the strict rankings accept) in EITHER direction check
(a->b and b->a must both agree), "invalid" otherwise.

    cd backend && .venv/bin/python3.9 scripts/eval_reference.py            # report
    cd backend && .venv/bin/python3.9 scripts/eval_reference.py --json out.json
"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import taxonomy

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "data", "reference_pairs.json")


def predict(a, b):
    ab, ba = taxonomy.substitution(a, b), taxonomy.substitution(b, a)
    lv = [x["level"] for x in (ab, ba) if x]
    return ("valid" if len(lv) == 2 and max(lv) <= 2 else "invalid"), (max(lv) if len(lv) == 2 else None)


def evaluate():
    rows = json.load(open(DATA))
    out = []
    for r in rows:
        pred, lvl = predict(r["a"], r["b"])
        out.append({**r, "pred": pred, "level": lvl, "ok": pred == r["label"]})
    return out


def main():
    res = evaluate()
    tp = sum(1 for r in res if r["label"] == "valid" and r["pred"] == "valid")
    fp = [r for r in res if r["label"] == "invalid" and r["pred"] == "valid"]
    fn = [r for r in res if r["label"] == "valid" and r["pred"] == "invalid"]
    tn = sum(1 for r in res if r["label"] == "invalid" and r["pred"] == "invalid")
    prec = tp / max(tp + len(fp), 1); rec = tp / max(tp + len(fn), 1)
    print(f"pairs {len(res)}  precision {prec:.3f}  recall {rec:.3f}  false-positives {len(fp)}  false-negatives {len(fn)}  true-negatives {tn}")
    lv = collections.Counter(r["level"] for r in res if r["pred"] == "valid")
    print("accepted by level:", dict(lv))
    for title, rows in (("FALSE POSITIVES (a bad alternative was accepted)", fp), ("FALSE NEGATIVES (a good alternative was refused)", fn)):
        print("\n" + title)
        for r in rows:
            print(f"  [{r['why']}] {r['a']['name']}  <->  {r['b']['name']}  (level {r['level']})")
    if "--json" in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
