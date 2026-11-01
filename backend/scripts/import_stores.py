"""Load EVERY French supermarket branch of the known chains into Mieux's stores table, from the OpenStreetMap shop list published on data.gouv.fr (magOSM).

    cd backend && .venv/bin/python -m scripts.import_stores            # downloads the list (about 50 MB), then imports
    cd backend && .venv/bin/python -m scripts.import_stores data/shops_point.csv

Why: asking OpenStreetMap's search box for "Carrefour" near you returns its 40 most 'important' matches, not the 40 nearest, so in a dense area the closest branch can be
missing. With the full list, the nearest branch is an exact distance query. Refresh every few months. Source: OpenStreetMap contributors (ODbL), via magOSM / Magellium."""
import csv
import os
import re
import sys
import urllib.request

from app import chains as ch
from app import db, retail

csv.field_size_limit(10 ** 8)
URL = ("https://magosm.magellium.com/geoserver/wfs?request=GetFeature&version=2.0.0&count=1000000&outputFormat=csv&typeName=magosm:shops_point&srsName=EPSG:4326"
       "&bbox=-1501530.3425145051,4785263.316753057,2607724.29809657,7033123.44456352")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KINDS = {"supermarket", "convenience", "department_store", "general", "variety_store", "wholesale", "greengrocer", "frozen_food"}
POINT = re.compile(r"POINT \(([-\d.]+) ([-\d.]+)\)")


def fetch() -> str:
    """The server returns at most 100 000 shops per request: page through the whole list (sorted, so pages never overlap)."""
    path = os.path.join(HERE, "data", "shops_point.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    page, start, total = 100000, 0, 0
    with open(path, "wb") as f:
        while True:
            url = URL.replace("count=1000000", f"count={page}&startIndex={start}&sortBy=osm_id")
            req = urllib.request.Request(url, headers={"User-Agent": "Mieux/0.2 (prototype)"})
            with urllib.request.urlopen(req, timeout=600) as r:
                body = r.read()
            lines = body.split(b"\n")
            n = max(0, len([x for x in lines if x.strip()]) - 1)
            f.write(body if start == 0 else b"\n".join(lines[1:]))
            if not body.endswith(b"\n"):
                f.write(b"\n")
            total += n
            print(f"  page at {start:,}: {n:,} shops", flush=True)
            if n < page:
                break
            start += page
    print(f"downloaded {total:,} shops")
    return path


def main(path: str) -> None:
    Session = db.make_session_factory()
    s = Session()
    retail.seed(s)
    rows, seen = [], 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            seen += 1
            if r.get("shop") not in KINDS:
                continue
            cname = ch.canon(r.get("brand")) or ch.canon(r.get("name")) or ch.canon(r.get("operator")) or ch.canon(r.get("short_name"))
            cid = retail.ID_OF.get(cname) if cname else None
            m = POINT.search(r.get("the_geom") or "")
            if not cid or not m:
                continue
            lon, lat = float(m.group(1)), float(m.group(2))
            addr = ", ".join(x for x in [" ".join(y for y in [r.get("addr-housenumber"), r.get("addr-street")] if y), " ".join(y for y in [r.get("addr-postcode"), r.get("addr-city")] if y)] if x)
            rows.append(dict(chain_id=cid, store_name=(r.get("name") or r.get("brand") or cname), address=addr or None, latitude=lat, longitude=lon, source="magosm", source_id="magosm" + str(r.get("osm_id"))))
    s.query(db.Store).delete()  # this list is complete and authoritative; the slower per-search lookups only remain as a fallback
    s.bulk_insert_mappings(db.Store, rows)
    s.commit()
    by = {}
    for x in rows:
        by[x["chain_id"]] = by.get(x["chain_id"], 0) + 1
    print(f"done: {len(rows):,} branches of {len(by)} chains kept out of {seen:,} shops")
    print(", ".join(f"{retail.NAME_OF[k]} {v:,}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else fetch())
