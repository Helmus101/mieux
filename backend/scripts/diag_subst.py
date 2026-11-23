"""Diagnose WHY cross-type alternatives pass the substitution gate, over the audit sample.

For each audited product with alternatives, reload both sides from off_local.db, recompute
taxonomy.substitution and record which branch admitted the pair:
  same_cat      identical cat: type
  head_word     head nouns equal (cat-involving pairs)
  untyped       _untyped_substitute name/category overlap
  cluster       rule-vs-rule cluster level
  other         anything else
"""
import json, sqlite3, sys, collections
sys.path.insert(0, '.')
from app import taxonomy
from app.products import normalize

res = json.load(open('/tmp/audit20k.json'))
con = sqlite3.connect('off_local.db')

def load(b):
    row = con.execute("select data from off_products where code=?", (b,)).fetchone()
    if not row:
        return None
    try:
        return normalize(json.loads(row[0]))
    except Exception:
        return None

stats = collections.Counter()
examples = collections.defaultdict(list)
checked = 0
for r in res:
    if r.get('err') or not r.get('alts') or not r.get('b'):
        continue
    orig = load(r['b'])
    if not orig:
        continue
    co = taxonomy.classify(orig)
    for a in r['alts'][:5]:
        cand = load(a.get('b'))
        if not cand:
            continue
        cc = taxonomy.classify(cand)
        ot, ct = co.get('type'), cc.get('type')
        if not ot or not ct or ot == ct:
            continue
        checked += 1
        cat_o = str(ot).startswith('cat:')
        cat_c = str(ct).startswith('cat:')
        sub = taxonomy.substitution(orig, cand)
        lv = sub['level'] if sub else None
        # which branch?
        if cat_o and cat_c and ot == ct:
            branch = 'same_cat'
        elif cat_o or cat_c:
            if taxonomy._head_word(orig) and taxonomy._head_word(orig) == taxonomy._head_word(cand):
                branch = 'head_word'
            else:
                branch = 'untyped_or_none'
        elif lv is not None:
            branch = 'cluster'
        else:
            branch = 'none'
        key = (branch, lv)
        stats[key] += 1
        if len(examples[key]) < 4:
            examples[key].append((r.get('n'), a.get('n'), ot, ct))

print('cross-type pairs checked:', checked)
for k, n in stats.most_common():
    print(f'{n:6}  branch={k[0]:<16} level={k[1]}')
    for e in examples[k]:
        print('        ', e[0], '=>', e[1], '|', e[2], '->', e[3])
