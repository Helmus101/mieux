import json
import os
import sqlite3
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import taxo1000  # noqa: E402


def test_product_type_matching():
    assert taxo1000.classify("Ricola pastilles gorge")["type"] == "P0677"          # pastilles pour la gorge
    assert taxo1000.classify("Pastilles pour la gorge au miel")["type"] == "P1028"  # the honey variant is more specific
    r = taxo1000.classify("Yaourt grec nature 0%")["type"]
    assert r and r.startswith("P")
    r = taxo1000.classify("Steak haché de bœuf 5%")["type"]
    assert r and taxo1000.node(r)["category"] and "Bœuf" in taxo1000.node(r)["category"]


def test_multiple_types_and_groups():
    r = taxo1000.classify("Steak haché de bœuf 5%")
    assert len(r["types"]) >= 2 and r["groups"]                                   # several specific types, shared substitution group(s)
    assert taxo1000.classify("Produit sans nom connu")["type"] is None             # no evidence -> no forced match


def test_taxonomy_index_build(tmp_path):
    off = tmp_path / "off.db"
    db = sqlite3.connect(off)
    db.execute("create table off_products(code text primary key, scans integer, data text)")
    rows = [("1", 9, json.dumps({"product_name": "Ricola pastilles gorge", "generic_name": "pastilles", "countries_tags": ["en:france"]})),
            ("2", 4, json.dumps({"product_name": "Yaourt grec nature", "countries_tags": ["en:france"]})),
            ("3", 1, json.dumps({"product_name": "zzqwxv inconnue", "countries_tags": ["en:france"]}))]
    db.executemany("insert into off_products values (?,?,?)", rows)
    db.commit(); db.close()
    env = dict(os.environ, OFF_LOCAL=str(off))
    subprocess.check_call([sys.executable, "scripts/build_taxonomy_index.py"], env=env, cwd=os.path.join(os.path.dirname(__file__), ".."))
    db = sqlite3.connect(off)
    got = dict(db.execute("select code, ptype from off_tax"))
    assert got["1"] == "P0677" and got["2"].startswith("P") and "3" not in got
    assert db.execute("select count(*) from off_tax where grp=(select grp from off_tax where code='1')").fetchone()[0] >= 1
    db.close()
