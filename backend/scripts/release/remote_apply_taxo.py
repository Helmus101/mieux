# Runs inside the Fly machine: swap the taxonomy index tables of /data/off_local.db for the freshly built ones in /data/taxo_index.db.
import sqlite3, time, os
t0 = time.time()
db = sqlite3.connect("/data/off_local.db", timeout=120)
db.execute("pragma busy_timeout=120000")
db.execute("attach database '/data/taxo_index.db' as src")
new_tax = db.execute("select count(*) from src.off_tax").fetchone()[0]
new_taxo = db.execute("select count(*) from src.off_taxo").fetchone()[0]
assert new_tax > 500000 and new_taxo > 1000000, (new_tax, new_taxo)
db.execute("begin immediate")
db.execute("drop table if exists main.off_tax")
db.execute("create table main.off_tax (code text, grp text, ptype text, scans integer, primary key (code, grp))")
db.execute("insert into main.off_tax select * from src.off_tax")
db.execute("create index off_tax_grp on off_tax (grp, scans desc)")
db.execute("drop table if exists main.off_taxo")
db.execute("create table main.off_taxo (code text primary key, type text, category text, department text, level integer, source text, scans integer)")
db.execute("insert into main.off_taxo select * from src.off_taxo")
db.execute("create index off_taxo_type on off_taxo (type, scans desc)")
db.execute("create index off_taxo_cat on off_taxo (category, scans desc)")
db.commit()
print("swapped:", db.execute("select count(*) from off_tax").fetchone(), db.execute("select count(*) from off_taxo").fetchone(), round(time.time() - t0), "s")
db.execute("detach database src")
os.remove("/data/taxo_index.db")
print("removed taxo_index.db")
