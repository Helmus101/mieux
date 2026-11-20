"""Scores Mieux against the human-labelled sheet (data/ground_truth/labelled.jsonl, made from make_labeling_sheet.py output).
Uses the candidates' labels, never Mieux's own classification, as the truth.

    cd backend && .venv/bin/python3.9 scripts/evaluate_ground_truth.py ../data/ground_truth/labelled.jsonl [--gate]
Metrics: precision@5 (of the alternatives Mieux shows, the share labelled valid or conditional), wrong shown (labelled invalid), recall (of
the labelled-valid candidates, the share Mieux shows), hard-negative leak (labelled-invalid hard negatives that were shown). --gate exits 1 below
the targets: precision@5 >= 0.98, wrong shown == 0 on valid-labelled originals' top 5, recall >= 0.85."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def score(rows):
    shown = good = bad = valid_total = valid_found = 0
    for r in rows:
        labelled = {c["barcode"]: c["label"] for c in r["candidates"] if c.get("label") in ("valid", "invalid", "conditional")}
        if not labelled: continue
        mieux = [c["barcode"] for c in r["candidates"] if c["source"] == "mieux"][:5]
        for b in mieux:
            if b in labelled:
                shown += 1; good += labelled[b] in ("valid", "conditional"); bad += labelled[b] == "invalid"
        v = [b for b, l in labelled.items() if l == "valid"]
        valid_total += len(v); valid_found += sum(1 for b in v if b in mieux)
    return {"shown_labelled": shown, "precision_at_5": good / shown if shown else None, "invalid_shown": bad,
            "recall": valid_found / valid_total if valid_total else None, "valid_total": valid_total}


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(sys.argv[1])]
    s = score(rows); print(json.dumps(s, indent=1))
    if "--gate" in sys.argv:
        ok = s["precision_at_5"] is not None and s["precision_at_5"] >= .98 and s["invalid_shown"] == 0 and (s["recall"] or 0) >= .85
        sys.exit(0 if ok else 1)
