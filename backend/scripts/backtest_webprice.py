"""How accurate is the Google-grounded Gemini price? Compares it with prices we KNOW (retailer exports and Open Prices, last 90 days).

    cd backend && .venv/bin/python -m scripts.backtest_webprice [N]       # key from backend/.env (GEMINI_API_KEY=...); default 200 products

Prints the share found, and the error of price per 100 g/ml: median, and the share within 10 %, 20 %, 30 %. Decide with these numbers whether to ship."""
import json
import os
import random
import sqlite3
import statistics
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def _load_env() -> None:
    """Reads backend/.env (KEY=value lines); real environment variables win."""
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main(n: int = 200) -> None:
    _load_env()
    from app import value, webprice
    from app.products import normalize
    if not webprice.enabled():
        sys.exit("Set GEMINI_API_KEY (or another web-price provider) in backend/.env first.")
    op = value.OpenPricesClient(local_path=os.path.join(HERE, "op_local.db"))
    off = sqlite3.connect(os.path.join(HERE, "off_local.db"))
    db = sqlite3.connect(os.path.join(HERE, "op_local.db"))
    codes = [r[0] for r in db.execute("select distinct code from op_items where date >= date('now','-90 day')")]
    random.seed(7); random.shuffle(codes)
    errs, tried, found = [], 0, 0
    for code in codes:
        if tried >= n:
            break
        r = off.execute("select data from off_products where code=?", (code,)).fetchone()
        if not r:
            continue
        raw = json.loads(r[0]); raw["code"] = code
        p = normalize(raw)
        q = p.get("quantity")
        truth = op.latest(code, (q["amount"], q["unit"])) if q else None
        if not truth or not truth.get("per100_cents"):
            continue
        tried += 1
        got = webprice.lookup(p, use_cache=False)
        if got:
            found += 1
            errs.append(abs(got["per100_cents"] - truth["per100_cents"]) / truth["per100_cents"])
    if not tried:
        sys.exit("no products to test")
    print(f"tried {tried}, found a price for {found} ({found / tried:.0%})" + (f"  [last API error: {webprice.last_error}]" if webprice.last_error else ""))
    if errs:
        print(f"median error {statistics.median(errs):.0%} | within 10%: {sum(e <= .1 for e in errs) / len(errs):.0%} | 20%: {sum(e <= .2 for e in errs) / len(errs):.0%} | 30%: {sum(e <= .3 for e in errs) / len(errs):.0%}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
