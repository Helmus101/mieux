"""Score Mieux's alternatives against human labels (benchmark/cases.json).
  python scripts/benchmark.py --template   print the candidates of every case, to be labelled by a person
  python scripts/benchmark.py              compute the metrics from the labels that exist
Targets (proposed, not measured): substitutes in top five >= 95 %, incompatible in top five = 0, price correctness >= 98 %, determinism 100 %."""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = os.environ.get("MIEUX_API", "https://mieuxmanger.vercel.app/v1")
HEAD = {"Content-Type": "application/json", "X-Session-Id": "benchmark", "X-Country": "FR"}
CASES = os.path.join(os.path.dirname(__file__), "..", "benchmark", "cases.json")


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=HEAD)
    return json.load(urllib.request.urlopen(req, timeout=120))


def alternatives(case):
    code = case.get("barcode") or call("/search?q=" + urllib.parse.quote(case["query"]))["products"][0]["id"]
    r = call(f"/products/{code}/alternatives", {"priorities": ["value"], "limit": 5})
    return code, r


def top(r, key):
    return [(e["product"]["barcode"], e["product"]["name"], e.get("price_per_100_cents"), (e.get("price_source") or {}).get("confidence")) for e in r["rankings"].get(key, [])[:5]]


def main():
    data = json.load(open(CASES))
    template = "--template" in sys.argv
    tot = {"top5": 0, "substitute": 0, "incompatible": 0, "price": 0, "price_ok": 0, "determinism": 0, "cases": 0}
    for case in data["cases"]:
        code, r = alternatives(case)
        again = alternatives(case)[1]
        tot["cases"] += 1
        same = all(top(r, k) == top(again, k) for k in ("budget", "value", "quality"))
        tot["determinism"] += int(same)
        print(f"\n## {case.get('query') or code} -> {r['original']['name'][:50]}  (deterministic: {same})")
        for key in ("budget", "value", "quality"):
            for barcode, name, p100, conf in top(r, key):
                lab = case["labels"].get(barcode, {})
                print(f"  {key:8} {barcode} {name[:44]:44} p100={p100} conf={conf} labels={lab or '-'}")
                if lab.get("substitute") is not None:
                    tot["top5"] += 1
                    tot["substitute"] += int(bool(lab["substitute"]))
                    tot["incompatible"] += int(lab["substitute"] is False)
                if lab.get("price_ok") is not None:
                    tot["price"] += 1
                    tot["price_ok"] += int(bool(lab["price_ok"]))
    if template:
        return
    pct = lambda a, b: "n/a (no labels yet)" if not b else f"{100 * a / b:.1f} %"  # noqa: E731
    print("\n== METRICS ==")
    print("genuine substitutes in top five :", pct(tot["substitute"], tot["top5"]), "(target >= 95 %)")
    print("incompatible products in top 5  :", tot["incompatible"], "(target 0)")
    print("price correctness               :", pct(tot["price_ok"], tot["price"]), "(target >= 98 %)")
    print("determinism                     :", pct(tot["determinism"], tot["cases"]), "(target 100 %)")


if __name__ == "__main__":
    main()
