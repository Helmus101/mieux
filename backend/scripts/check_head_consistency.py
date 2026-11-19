"""Head-word consistency over ALL types: the first meaningful word of a product name usually names the product ("yaourt", "huile", "biscuits").
For every such word seen in >= MIN products where one type holds >= DOM of them, the products of that word typed elsewhere are listed:
they are either legitimate dishes ("Biscuits au thé") or classifier mistakes. Sorted by how many are off, with samples.

    cd backend && .venv/bin/python scripts/check_head_consistency.py [MIN] [DOM]
"""
import collections, os, re, sqlite3, sys, unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("OFF_LOCAL", os.path.join(HERE, "off_local.db"))
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 60
DOM = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
SKIP = set("le la les un une des du de d l au aux et bio extra the a an with sans avec pur pure petit petits petite petites grand grande mini maxi nouveau nos mon ma mes".split())


def norm(t):
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", t)


def main():
    db = sqlite3.connect(DB)
    types = {c: t for c, t in db.execute("select code, type from off_type")}
    by = collections.defaultdict(collections.Counter)
    ex = collections.defaultdict(list)
    for code, text in db.execute("select code, text from off_names"):
        t = types.get(code)
        if not t:
            continue
        ws = [w for w in norm(text or "").split() if w not in SKIP and len(w) > 2]
        if not ws:
            continue
        by[ws[0]][t] += 1
        if len(ex[(ws[0], t)]) < 3:
            ex[(ws[0], t)].append((text or "")[:36])
    rows = []
    for w, c in by.items():
        n = sum(c.values())
        top, k = c.most_common(1)[0]
        if n >= MIN and k / n >= DOM and k < n:
            off = [(t, v) for t, v in c.most_common()[1:6]]
            rows.append((n - k, w, top, n, off))
    for bad, w, top, n, off in sorted(rows, reverse=True)[:70]:
        print(f"{w!r:16} {top:18} {bad:5} off of {n:<6}", "; ".join(f"{t}:{v} e.g. {ex[(w, t)][0]}" for t, v in off[:3]))
    print(f"\n{len(rows)} head words with a dominant type and some products elsewhere")


if __name__ == "__main__":
    main()
