"""Builds app/data/cat_groups.json: for each Open Food Facts category tag, the named Mieux type that most products carrying
that tag were given by a type rule (only when >= 70% of at least 5 rule-typed products agree). The classifier uses it so that a
product typed only by a fine tag ("cat:en:fries") and a product typed by a rule ("frozen_fries") are recognised as the same group.

    cd backend && .venv/bin/python3.9 -m scripts.build_cat_groups
"""
import collections, json, os, sqlite3, sys

sys.path.insert(0, ".")
OFF = os.environ.get("OFF_LOCAL", "off_local.db")
OUT = os.path.join("app", "data", "cat_groups.json")


def main():
    con = sqlite3.connect(OFF)
    typ = dict(con.execute("select code, type from off_type where type not like 'cat:%' and confidence in ('high','medium')"))
    votes = collections.defaultdict(collections.Counter)
    n = 0
    for code, data in con.execute("select code, data from off_products"):
        t = typ.get(code)
        if not t:
            continue
        try:
            tags = json.loads(data).get("categories_tags") or []
        except Exception:
            continue
        for tag in tags:
            votes[tag][t] += 1
        n += 1
        if n % 100000 == 0:
            print(n, flush=True)
    out = {}
    for tag, c in votes.items():
        total = sum(c.values())
        t, k = c.most_common(1)[0]
        if total >= 5 and k / total >= 0.7:
            out["cat:" + tag] = t
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), sort_keys=True, indent=0)
    print("tags with a group:", len(out), "of", len(votes))


if __name__ == "__main__":
    main()
