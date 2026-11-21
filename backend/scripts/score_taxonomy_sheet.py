"""Accuracy per department from a filled taxonomy_sheet.csv (column `correct` = y/n; blank rows are skipped).

    cd backend && .venv/bin/python -m scripts.score_taxonomy_sheet taxonomy_sheet.csv
"""
import collections, csv, sys
rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if (r.get("correct") or "").strip().lower() in ("y", "n", "yes", "no", "o", "oui", "non")]
agg = collections.defaultdict(lambda: [0, 0])
lvl = collections.defaultdict(lambda: [0, 0])
for r in rows:
    ok = r["correct"].strip().lower() in ("y", "yes", "o", "oui")
    for k, d in ((r["department"], agg), (f"level {r['level']}", lvl)):
        d[k][0] += ok
        d[k][1] += 1
print(f"{len(rows)} checked rows")
for title, d in (("by department", agg), ("by level", lvl)):
    print(f"\n{title}")
    for k, (ok, n) in sorted(d.items(), key=lambda kv: kv[1][0] / max(1, kv[1][1])):
        print(f"  {100 * ok / n:5.1f}%  {ok:3}/{n:<3}  {k}")
tot = sum(v[1] for v in agg.values())
print(f"\noverall: {100 * sum(v[0] for v in agg.values()) / max(1, tot):.1f}%")
for r in [r for r in rows if r["correct"].strip().lower() in ("n", "no", "non")][:40]:
    print("  WRONG:", r["name"][:50], "->", r["chosen"][-50:], "| should be:", r["right_type"])
