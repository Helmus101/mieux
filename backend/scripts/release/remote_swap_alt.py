# Runs inside the Fly machine: swap /data/alt_index.db.new in, keeping a timestamped copy of the index it replaces.
import glob, os, sqlite3, time
new, cur = "/data/alt_index.db.new", "/data/alt_index.db"
c = sqlite3.connect(f"file:{new}?mode=ro", uri=True)
n = c.execute("select count(*) from alt").fetchone()[0]; g = c.execute("select count(distinct grp) from alt_tax").fetchone()[0]
assert n > 40000 and g > 100, (n, g)
c.close()
bak = f"/data/alt_index.db.prev-{time.strftime('%Y%m%d-%H%M%S')}"
os.link(cur, bak)          # keep the old index for a rollback
os.replace(new, cur)       # atomic: the API reopens the file when it changes
for old in sorted(glob.glob("/data/alt_index.db.prev-*"))[:-3]:   # keep the three latest
    os.remove(old)
print("alt_index swapped:", n, "products,", g, "groups; backup:", bak)
