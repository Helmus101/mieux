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


def pct(a, b):
    return "n/a (0 labelled)" if not b else f"{100 * a / b:.1f} % (n={b})"


class Tally:
    """Counts of labelled yes/no answers, by metric."""
    def __init__(self):
        self.n, self.yes = {}, {}

    def add(self, metric, value):
        if value is None:
            return
        self.n[metric] = self.n.get(metric, 0) + 1
        self.yes[metric] = self.yes.get(metric, 0) + int(bool(value))

    def line(self, metric):
        return pct(self.yes.get(metric, 0), self.n.get(metric, 0))


# which label judges which ranking list (a "yes" is what the list promises)
LIST_LABEL = {"budget": "cheaper", "quality": "better_quality", "value": "good_value"}


def main():
    data = json.load(open(CASES))
    template = "--template" in sys.argv
    overall, by_cat, det = Tally(), {}, [0, 0]
    for case in data["cases"]:
        code, r = alternatives(case)
        again = alternatives(case)[1]
        cat = case.get("category") or case.get("query") or code
        tally = by_cat.setdefault(cat, Tally())
        same = all(top(r, k) == top(again, k) for k in LIST_LABEL)
        det[0] += int(same)
        det[1] += 1
        print(f"\n## {case.get('query') or code} -> {r['original']['name'][:50]}  (deterministic: {same})")
        seen = set()
        for key in LIST_LABEL:
            for barcode, name, p100, conf in top(r, key):
                lab = case["labels"].get(barcode, {})
                print(f"  {key:8} {barcode} {name[:44]:44} p100={p100} conf={conf} labels={lab or '-'}")
                for t in (overall, tally):
                    t.add("list:" + key + ":" + LIST_LABEL[key], lab.get(LIST_LABEL[key]))   # judged per list: the same product in two lists is judged for each promise
                if barcode in seen:                                                           # product-level facts are counted once per scanned product, not once per list
                    continue
                seen.add(barcode)
                for t in (overall, tally):
                    t.add("substitute", lab.get("substitute"))
                    t.add("price_ok", lab.get("price_ok"))
    if template:
        return
    print("\n== METRICS (sample sizes shown; small n proves nothing) ==")
    print("genuine substitutes in top five :", overall.line("substitute"), "(target >= 95 %)")
    inc = overall.n.get("substitute", 0) - overall.yes.get("substitute", 0)
    print("incompatible products in top 5  :", inc if overall.n.get("substitute") else "n/a (0 labelled)", "(target 0)")
    print("price correctness               :", overall.line("price_ok"), "(target >= 98 %)")
    for key, label in LIST_LABEL.items():
        print(f"{key:8} list judged '{label}':", overall.line(f"list:{key}:{label}"))
    print("determinism                     :", pct(det[0], det[1]))
    print("\n-- by category --")
    for cat, t in by_cat.items():
        print(f"  {cat:24} substitutes {t.line('substitute'):22} price {t.line('price_ok')}")


if __name__ == "__main__":
    main()
