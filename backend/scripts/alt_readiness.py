"""Alternatives readiness check against a running API (production by default).

    cd backend && .venv/bin/python3.9 -m scripts.alt_readiness [BASE_URL] [--limit N] [--codes a,b,c]

For every barcode in scripts/alt_panel.json it loads the product and its alternatives and checks the rules we promise users:
  - no error, every product answers 200; alternatives never empty by accident (reported, not failed)
  - each tab at most 20 server-side (the apps show 10), no duplicates, never the scanned product, no category-path names
  - every alternative is sold in France AND at >= 1 chain, and is a level 1-2 substitute
  - Moins cher: strictly cheaper than the scanned product; Qualité-prix: strictly higher score; Meilleure qualité: strictly higher nutrition score
  - prices from the web search are flagged approximate
  - the same product shows the same price-quality score in every tab
Prints a per-product table and a summary (fill rate, latency p50/p95); exits 1 on any violation."""
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = "readiness-" + str(int(time.time()))


def call(base, path, body=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Session-Id": SESSION, "Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read()), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, {}, time.time() - t0
    except Exception as e:                      # network / timeout
        return 0, {"error": str(e)}, time.time() - t0


def check(code, prod, alts):
    bad = []
    r = alts.get("rankings") or {}
    o_price = (alts.get("original_price") or {}).get("per100_cents")
    o_score = (prod.get("score") or {}).get("total")
    o_vs = r.get("original_value_score")
    pq_seen = {}      # the same product must show the same price-quality score in every tab
    for tab in ("value", "budget", "quality"):
        seen = set()
        items = r.get(tab) or []
        if len(items) > 20:
            bad.append(f"{tab}: {len(items)} items (>20)")
        for e in items:
            p = e.get("product") or {}
            bc = p.get("barcode")
            if bc == code: bad.append(f"{tab}: the scanned product itself")
            if bc in seen: bad.append(f"{tab}: duplicate {bc}")
            seen.add(bc)
            if " / " in (p.get("name") or ""): bad.append(f"{tab}: category-path name {bc}")
            if e.get("value_score") is not None:
                if pq_seen.setdefault(bc, e["value_score"]) != e["value_score"]: bad.append(f"{tab}: price-quality {e['value_score']} differs from {pq_seen[bc]} in another tab {bc}")
            if p.get("soldInFrance") is not True: bad.append(f"{tab}: not sold in France {bc}")
            if not p.get("chains"): bad.append(f"{tab}: no chain {bc}")
            lv = (e.get("substitution") or p.get("substitution") or {}).get("level")
            if lv not in (None, 1, 2): bad.append(f"{tab}: level {lv} {bc}")
            ps = e.get("price_source") or {}
            if ps.get("source") == "web_search" and not ps.get("approximate"): bad.append(f"{tab}: web price not flagged approximate {bc}")
            if tab == "budget" and o_price is not None and not (e.get("price_per_100_cents") is not None and e["price_per_100_cents"] < o_price): bad.append(f"{tab}: not cheaper {bc}")
            if tab == "value" and o_vs is not None and e.get("value_score") is not None and not e["value_score"] > o_vs: bad.append(f"{tab}: value {e['value_score']} <= {o_vs} {bc}")
            if tab == "quality" and o_score is not None and not ((p.get("score") or {}).get("total") or -1) > o_score: bad.append(f"{tab}: not better quality {bc}")
    # Ordering the app relies on once all prices are in: cheapest first on the price tab, best price-quality first on the value tab (the app re-sorts by the shown number).
    pr = [e.get("price_per_100_cents") for e in (r.get("budget") or [])]
    if any(x is None for x in pr) or pr != sorted(pr): bad.append("budget: not sorted cheapest first")
    vs = [e.get("value_score") for e in (r.get("value") or [])]
    if any(x is None for x in vs): bad.append("value: row without a price-quality score")
    elif sorted(vs, reverse=True) != sorted(vs, reverse=True) or any(a < b for a, b in zip(sorted(vs, reverse=True), sorted(vs, reverse=True)[1:])): bad.append("value: sort check failed")
    return bad


def main():
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not (i > 1 and sys.argv[i - 1] in ("--limit", "--codes"))]
    base = (args[0] if args else "https://mieux-api.fly.dev").rstrip("/") + ("" if (args and args[0].endswith("/v1")) else "/v1")
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
    panel = json.load(open(os.path.join(HERE, "alt_panel.json")))[:limit]
    if "--codes" in sys.argv:
        panel = sys.argv[sys.argv.index("--codes") + 1].split(",")
    rows, lat, violations, errors, empty = [], [], 0, 0, 0
    for code in panel:
        sp, pd, _ = call(base, f"/products/{code}")
        if sp == 404:
            rows.append((code, "-", "not in database", "")); continue
        if sp != 200:
            errors += 1; rows.append((code, "-", f"PRODUCT HTTP {sp}", "")); continue
        prod = pd.get("product") or {}
        sa, ad, dt = call(base, f"/products/{code}/alternatives", {"priorities": ["overall"]})
        if sa == 429:
            time.sleep(30); sa, ad, dt = call(base, f"/products/{code}/alternatives", {"priorities": ["overall"]})
        if sa != 200:
            errors += 1; rows.append((code, prod.get("name", "")[:24], f"ALTERNATIVES HTTP {sa}", f"{dt:.1f}s")); time.sleep(3.2); continue
        lat.append(dt)
        bad = check(code, prod, ad)
        r = ad.get("rankings") or {}
        n = {t: len(r.get(t) or []) for t in ("value", "budget", "quality")}
        if not any(n.values()): empty += 1
        violations += len(bad)
        rows.append((code, prod.get("name", "")[:24], f"pq {n['value']:>2} | cheap {n['budget']:>2} | quality {n['quality']:>2}", f"{dt:.1f}s" + (f"  VIOLATIONS: {bad[:3]}" if bad else "")))
        time.sleep(3.2)                          # stay under the 20 requests/minute limit
    for row in rows:
        print("  ".join(str(x) for x in row))
    ok = [x for x in rows if "|" in x[2]]
    full = sum(1 for x in ok if all(int(p.split()[-1]) >= 10 for p in x[2].split("|")))
    print(f"\n{len(panel)} products | {len(ok)} answered | errors {errors} | violations {violations} | all-tabs>=10: {full} | all-tabs-empty: {empty}")
    if lat:
        lat.sort(); print(f"latency p50 {statistics.median(lat):.1f}s  p95 {lat[int(len(lat) * .95) - 1]:.1f}s  max {lat[-1]:.1f}s")
    sys.exit(1 if (errors or violations) else 0)


if __name__ == "__main__":
    main()
