"""Audit taxonomy coverage and obvious misclassifications over the whole OFF copy.

Usage: python -m scripts.audit_taxonomy [--limit N] [--sample N]
Prints coverage by source/confidence and the most frequent suspicious name->type mismatches.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
OFF = os.environ.get("OFF_LOCAL", os.path.join(HERE, "..", "off_local.db"))

from app import taxonomy

# Name says X strongly; any other type is suspicious. Keep these few and unambiguous.
EXPECT = [
    ("rice_pudding", re.compile(r"\briz au lait\b|rice pudding", re.I)),
    ("oil", re.compile(r"\bhuile\b[^,;]{0,20}\b(olive|colza|tournesol|arachide|noix)\b|\bhuile d.olive\b|olive oil|huile vegetale|huile de colza|huile de tournesol", re.I)),
    ("compote", re.compile(r"\bcompotes?\b", re.I)),
    ("jam", re.compile(r"\bconfiture\b|\bmarmelade\b|\bjam\b", re.I)),
    ("honey", re.compile(r"\bmiel\b(?!\s+(?:et|aux|a)\b)", re.I)),
    ("butter", re.compile(r"^beurre\b|beurre doux|beurre demi-sel", re.I)),
    ("yogurt", re.compile(r"\byaourts?\b|\byogurt\b|\byoghurt\b|petit suisse", re.I)),
    ("milk", re.compile(r"^lait\b|\blait (de|d.)(vache|brebis|chevre|chèvre|jument)", re.I)),
    ("cheese", re.compile(r"\bfromage\b", re.I)),
    ("bread", re.compile(r"\bpain\b|baguette|brioche\b", re.I)),
    ("pasta", re.compile(r"\bp[âa]tes?\b|spaghetti|penne|fusilli", re.I)),
    ("rice", re.compile(r"^riz\b(?!\s+au\s+lait)|\briz (basmati|complet|long|thai|rouge|noir|gluant|arborio|bomba)", re.I)),
    ("soda", re.compile(r"\bcola\b|\bcoca.?cola\b|\bfanta\b|\bsprite\b|\borangina\b|limonade", re.I)),
    ("coffee", re.compile(r"\bcaf[ée]\b|espresso|cappuccino", re.I)),
    ("tea", re.compile(r"\bth[ée]\b|thé glace|infusion", re.I)),
    ("beer", re.compile(r"\bbi[èe]re\b|\bbeer\b|pale ale|\bipa\b|lager", re.I)),
    ("wine", re.compile(r"\bvin\b|\bwine\b|champagne|ros[ée]\b|prosecco", re.I)),
    ("chicken", re.compile(r"\bpoulet\b|\bchicken\b", re.I)),
    ("beef", re.compile(r"\bb[œo]uf\b|\bbeef\b", re.I)),
    ("pork", re.compile(r"\bporc\b|\bpork\b|carr[ée]\b.{0,10}\bporc", re.I)),
    ("fish_canned", re.compile(r"\bsardines?\b|\bthon\b|\bmaquereaux?\b", re.I)),
    ("water", re.compile(r"^eau\b|eau (min[ée]rale|de source|gazeuse|plate|p[ée]tillante)", re.I)),
    ("chips", re.compile(r"\bchips?\b|\bcrisps?\b", re.I)),
    ("chocolate_spread", re.compile(r"p[âa]te [àa] tartiner|nutella|pasta cao", re.I)),
    ("ice_cream", re.compile(r"\bglaces?\b|sorbet|ice cream", re.I)),
    ("soup", re.compile(r"\bsoupes?\b|\bvelout[ée]s?\b", re.I)),
    ("baby_food", re.compile(r"\bnutricia\b|\bbl[ée]dina\b|petit pot", re.I)),
]

_FAMILY_OK = {"yogurt": {"yogurt", "fromage_blanc", "kefir", "flavoured_yogurt", "plain_yogurt", "plant_yogurt"}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-scans", type=int, default=0)
    args = ap.parse_args()
    if not os.path.exists(OFF):
        sys.exit(f"no OFF copy at {OFF}")

    db = sqlite3.connect(OFF)
    sql = "select code, scans, data from off_products"
    if args.min_scans:
        sql += f" where scans >= {args.min_scans}"
    t0 = time.time()
    cov = Counter()
    bad = Counter()
    bad_ex = {}
    n = typed = 0
    for code, scans, data in db.execute(sql):
        n += 1
        if args.limit and n > args.limit:
            break
        try:
            r = json.loads(data)
        except ValueError:
            continue
        name = r.get("product_name") or ""
        if not name:
            continue
        p = {"categories": r.get("categories_tags") or [], "name": name, "brand": r.get("brands"), "generic_name": r.get("generic_name")}
        cl = taxonomy.classify(p)
        tid = cl.get("type")
        src = cl.get("source", "?")
        cov[("typed" if tid else "untyped", src, cl.get("confidence", "?"))] += 1
        if tid:
            typed += 1
        # Suspicious: name strongly says a different type.
        for want, rx in EXPECT:
            if not rx.search(name):
                continue
            if want == "yogurt":
                ok = tid in _FAMILY_OK["yogurt"]
            elif want == "coffee":
                ok = bool(tid) and ("coffee" in str(tid) or tid in ("capsule_nespresso", "capsule_dolce_gusto", "capsule_tassimo", "pods_senseo", "capsule_other", "instant_coffee", "coffee_beans", "ground_coffee"))
            elif want == "cheese":
                ok = tid in taxonomy._CHEESE_TYPES or tid in ("fromage_blanc", "cream_cheese", "feta", "parmesan")
            elif want == "bread":
                ok = tid in ("baguette", "bread", "brioche", "croissant", "toast", "bun", "bun", "sandwich_bread", "flatbread", "pita", "wrap", "tortilla", "pizza_dough", "breadsticks", "crackers", "sweet_biscuits", "crispbread") or "bread" in str(tid)
            else:
                ok = tid == want
            if not ok:
                key = f"{name[:0]}{want} -> {tid}"
                bad[key] += 1
                bad_ex.setdefault(key, name[:60])
        if n % 200000 == 0:
            print(f"  {n} read, {typed} typed ({time.time() - t0:.0f} s)", flush=True)

    print(f"\n== coverage: {typed}/{n} typed ({100 * typed / max(1, n):.1f}%) in {time.time() - t0:.0f}s")
    for (t, src, conf), c in cov.most_common(15):
        print(f"  {t:8} {src:15} {conf:8} {c}")
    print("\n== suspicious (name says X, classified Y):")
    for k, c in bad.most_common(40):
        print(f"  {c:6}  {k:35} e.g. {bad_ex[k]}")


if __name__ == "__main__":
    main()
