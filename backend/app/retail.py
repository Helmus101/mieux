"""Chain discovery and nearest-branch search, kept as two independent questions.
1. Which chains list this product?  -> chain_product_listings (evidence-based: community sighting by EAN, the chain's own brand, user confirmation;
   retailer catalogue adapters plug in through CATALOGUES when a chain gives permitted access).
2. Where is the nearest branch of each?  -> stores (OpenStreetMap, cached in our own table, so a repeat search is instant)."""
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from . import chains as ch
from . import market
from . import db

SEED = [  # id, name, website, has_catalogue, catalogue_access
    ("carrefour", "Carrefour", "https://www.carrefour.fr", True, "blocked"), ("monoprix", "Monoprix", "https://www.monoprix.fr", True, "blocked"),
    ("intermarche", "Intermarché", "https://www.intermarche.com", True, "blocked"), ("leclerc", "E.Leclerc", "https://www.e.leclerc", True, "blocked"),
    ("auchan", "Auchan", "https://www.auchan.fr", True, "blocked"), ("lidl", "Lidl", "https://www.lidl.fr", True, "none"), ("aldi", "Aldi", "https://www.aldi.fr", False, "none"),
    ("franprix", "Franprix", "https://www.franprix.fr", True, "none"), ("casino", "Casino", "https://www.casino.fr", True, "none"), ("superu", "Super U", "https://www.coursesu.com", True, "blocked"),
    ("picard", "Picard", "https://www.picard.fr", True, "none"), ("biocoop", "Biocoop", "https://www.biocoop.fr", False, "none"),
    ("naturalia", "Naturalia", "https://www.naturalia.fr", True, "none"), ("lavieclaire", "La Vie Claire", "https://www.lavieclaire.com", True, "none"), ("grandfrais", "Grand Frais", "https://www.grandfrais.com", False, "none"), ("cora", "Cora", "https://www.cora.fr", True, "none"), ("match", "Match", "https://www.supermarchesmatch.fr", False, "none"),
    ("walmart", "Walmart", "https://www.walmart.com", False, "none"), ("kroger", "Kroger", "https://www.kroger.com", False, "none"), ("costco", "Costco", "https://www.costco.com", False, "none"),
    ("target", "Target", "https://www.target.com", False, "none"), ("albertsons", "Albertsons", "https://www.albertsons.com", False, "none"), ("safeway", "Safeway", "https://www.safeway.com", False, "none"),
    ("publix", "Publix", "https://www.publix.com", False, "none"), ("wholefoods", "Whole Foods", "https://www.wholefoodsmarket.com", False, "none"),
    ("traderjoes", "Trader Joe's", "https://www.traderjoes.com", False, "none"), ("heb", "H-E-B", "https://www.heb.com", False, "none"), ("wegmans", "Wegmans", "https://www.wegmans.com", False, "none"),
    ("sprouts", "Sprouts", "https://www.sprouts.com", False, "none"), ("foodlion", "Food Lion", "https://www.foodlion.com", False, "none"), ("stopshop", "Stop & Shop", "https://www.stopandshop.com", False, "none"),
    ("meijer", "Meijer", "https://www.meijer.com", False, "none"), ("sams", "Sam's Club", "https://www.samsclub.com", False, "none"), ("bjs", "BJ's", "https://www.bjs.com", False, "none"),
    ("hyvee", "Hy-Vee", "https://www.hy-vee.com", False, "none"), ("shoprite", "ShopRite", "https://www.shoprite.com", False, "none"), ("harristeeter", "Harris Teeter", "https://www.harristeeter.com", False, "none"),
    ("winndixie", "Winn-Dixie", "https://www.winndixie.com", False, "none"),
]
ID_OF = {"Carrefour": "carrefour", "Monoprix": "monoprix", "Intermarché": "intermarche", "E.Leclerc": "leclerc", "Auchan": "auchan", "Lidl": "lidl", "Aldi": "aldi", "Franprix": "franprix",
         "Casino": "casino", "Super U": "superu", "Picard": "picard", "Biocoop": "biocoop", "Naturalia": "naturalia", "La Vie Claire": "lavieclaire", "Grand Frais": "grandfrais", "Cora": "cora", "Match": "match",
         "Walmart": "walmart", "Kroger": "kroger", "Costco": "costco", "Target": "target", "Albertsons": "albertsons", "Safeway": "safeway", "Publix": "publix", "Whole Foods": "wholefoods",
         "Trader Joe's": "traderjoes", "H-E-B": "heb", "Wegmans": "wegmans", "Sprouts": "sprouts", "Food Lion": "foodlion", "Stop & Shop": "stopshop", "Meijer": "meijer", "Sam's Club": "sams",
         "BJ's": "bjs", "Hy-Vee": "hyvee", "ShopRite": "shoprite", "Harris Teeter": "harristeeter", "Winn-Dixie": "winndixie"}
NAME_OF = {v: k for k, v in ID_OF.items()}
US_IDS = {"walmart", "kroger", "costco", "target", "albertsons", "safeway", "publix", "wholefoods", "traderjoes", "heb", "wegmans", "sprouts", "foodlion", "stopshop", "meijer", "sams", "bjs",
          "hyvee", "shoprite", "harristeeter", "winndixie", "aldi", "lidl"}  # Aldi and Lidl trade in both countries
FR_ONLY = {"carrefour", "monoprix", "intermarche", "leclerc", "auchan", "franprix", "casino", "superu", "picard", "biocoop", "naturalia", "lavieclaire", "grandfrais", "cora", "match"}


def in_market(chain_id: str, code: str = "FR") -> bool:
    """Is this chain one the shoppers of this market know? French shoppers never see US chains, and the other way round."""
    return chain_id in US_IDS if code == "US" else chain_id not in (US_IDS - {"aldi", "lidl"})
_EMPTY: Dict[Any, float] = {}
CATALOGUES: Dict[str, Any] = {}  # chain id -> adapter(product) -> {"retailer_product_id", "url", "price_per100_cents"} | None. Empty: no chain currently allows automated access.


def seed(s: Session) -> None:
    have = {c.id for c in s.query(db.RetailChain).all()}
    for cid, name, web, cat, acc in SEED:
        if cid not in have:
            s.add(db.RetailChain(id=cid, name=name, website=web, has_catalogue=cat, catalogue_access=acc))
    s.commit()


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    return ch.haversine_km(lat1, lon1, lat2, lon2) * 1000


# ---------------------------------------------------------------- 1. chain discovery
def discover(s: Session, product: Dict[str, Any], sightings: List[Dict[str, Any]]) -> List[db.ChainProductListing]:
    """Upsert the evidence we can legitimately gather, then return every stored listing for the product. Nothing is guessed."""
    pid = product["id"]
    rows = {r.chain_id: r for r in s.query(db.ChainProductListing).filter_by(product_id=pid).all()}

    def upsert(chain_id: str, **kw) -> None:
        r = rows.get(chain_id)
        rank = {"user_confirmed": 3, "exact_ean": 2, "own_brand": 1}
        if r and rank.get(r.match_type, 0) > rank.get(kw.get("match_type"), 0) and r.listing_status == "listed":
            r.last_checked = datetime.utcnow()  # keep the stronger evidence
            return
        if not r:
            r = db.ChainProductListing(product_id=pid, chain_id=chain_id)
            s.add(r)
            rows[chain_id] = r
        for k, v in kw.items():
            setattr(r, k, v)
        r.last_checked = datetime.utcnow()

    for st in sightings:  # a community price seen in France under this exact EAN in any shop of the chain: the chain lists it (assumed for all its branches)
        cname = ch.canon(st.get("chain") or st.get("store") or st.get("name"))
        if cname in ID_OF:
            upsert(ID_OF[cname], match_type="exact_ean", match_confidence=1.0, listing_status="listed", source="open_prices", price_per100_cents=st.get("per100_cents"),
                   note=f"{st.get('observations', 1)} relevé(s), {st.get('shops', 1)} magasin(s)")
    own = ch.own_brand_chain(product.get("brand"))
    if own in ID_OF:  # the chain's own brand is only sold by that chain
        upsert(ID_OF[own], match_type="own_brand", match_confidence=0.9, listing_status="listed", source="own_brand")
    for cid, adapter in CATALOGUES.items():  # permitted retailer catalogues (none shipped: see catalogue_access)
        try:
            hit = adapter(product)
        except Exception:
            hit = None
        if hit:
            upsert(cid, match_type="exact_ean", match_confidence=1.0, listing_status="listed", source="retailer_catalogue", retailer_product_id=hit.get("retailer_product_id"),
                   source_url=hit.get("url"), price_per100_cents=hit.get("price_per100_cents"))
    s.commit()
    return list(rows.values())


def confirm(s: Session, product_id: str, chain_id: str, url: Optional[str] = None) -> db.ChainProductListing:
    """A user says they found the product in this chain. Stored as evidence (user_confirmed), never silently overriding an exact-EAN match."""
    r = s.query(db.ChainProductListing).filter_by(product_id=product_id, chain_id=chain_id).first()
    if not r:
        r = db.ChainProductListing(product_id=product_id, chain_id=chain_id)
        s.add(r)
    if r.match_type != "exact_ean" or r.listing_status != "listed":
        r.match_type, r.match_confidence, r.source = "user_confirmed", 0.8, "user"
    r.listing_status, r.last_checked = "listed", datetime.utcnow()
    if url:
        r.source_url = url
    s.commit()
    return r


# ---------------------------------------------------------------- 2. geographic discovery (stores table = cache of OpenStreetMap)
def _near(s: Session, chain_id: str, lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    q = s.query(db.Store).filter(db.Store.chain_id == chain_id, db.Store.active.is_(True), db.Store.latitude.between(lat - dlat, lat + dlat), db.Store.longitude.between(lon - dlon, lon + dlon))
    out = []
    for r in q.all():
        d = haversine_m(lat, lon, r.latitude, r.longitude)
        if d <= radius_km * 1000:
            out.append({"name": r.store_name or NAME_OF.get(chain_id), "address": r.address, "lat": r.latitude, "lon": r.longitude, "distance_m": round(d), "store_id": r.id})
    return sorted(out, key=lambda x: x["distance_m"])


def _fetch_and_store(s: Session, chain_id: str, lat: float, lon: float, radius_km: float, widen: bool = True) -> int:
    """Ask OpenStreetMap (Nominatim, one request per step) and save every branch found; widen the box only when nothing is known yet."""
    cname = NAME_OF[chain_id]
    added = 0
    for r_km in (sorted({min(radius_km, x) for x in (1.5, radius_km)}) if widen else [radius_km]):  # widening boxes: the first one that holds a branch holds the nearest
        dlat, dlon = r_km / 111.0, r_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
        try:
            res = ch._get_json(ch._NOMINATIM, {"q": ch.QUERY.get(cname, cname), "format": "jsonv2", "limit": 40, "addressdetails": 1, "countrycodes": market.current().lower(),
                                               "viewbox": f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}", "bounded": 1})
        except Exception:
            res = []
        found = False
        for el in res or []:
            if ch.canon(el.get("name") or el.get("display_name", "").split(",")[0]) != cname:
                continue
            sid = f"{el.get('osm_type', 'x')}{el.get('osm_id', el.get('place_id'))}"
            if s.query(db.Store.id).filter_by(source_id=sid).first():
                found = True
                continue
            a = el.get("address") or {}
            addr = ", ".join(x for x in [" ".join(y for y in [a.get("house_number"), a.get("road")] if y), a.get("city") or a.get("town") or a.get("village")] if x)
            s.add(db.Store(chain_id=chain_id, store_name=el.get("name") or cname, address=addr or None, latitude=float(el["lat"]), longitude=float(el["lon"]), source="openstreetmap", source_id=sid))
            added += 1
            found = True
        s.commit()
        if found:
            break
        time.sleep(1.0)  # Nominatim policy: at most one request per second
    return added


WIDEN = (80.0, 250.0)  # when nothing is found nearby, look further (a chain listed in France may have no branch in your town)


def nearest(s: Session, chain_id: str, lat: float, lon: float, radius_km: float, k: int = 2, refresh: bool = True, widen: bool = True) -> List[Dict[str, Any]]:
    """Closest branches of the chain. Order: stored branches near you; if none, ask OpenStreetMap near you (unless that was empty within the hour);
    only then widen (80 km, 250 km), fetching those wider areas too. A far branch already stored never hides a nearer one that was never looked up."""
    near = _near(s, chain_id, lat, lon, radius_km)
    key = (chain_id, round(lat, 2), round(lon, 2), radius_km)
    fresh_empty = time.time() - _EMPTY.get(key, 0) <= 3600
    if not near and refresh and not fresh_empty:
        _fetch_and_store(s, chain_id, lat, lon, radius_km)
        near = _near(s, chain_id, lat, lon, radius_km)
    if not near and not widen:
        return []  # strict radius: nothing inside it, nothing returned
    if not near:
        for far in WIDEN:
            if far <= radius_km:
                continue
            near = _near(s, chain_id, lat, lon, far)
            if not near and refresh and not fresh_empty:
                time.sleep(1.0)
                _fetch_and_store(s, chain_id, lat, lon, far, widen=False)
                near = _near(s, chain_id, lat, lon, far)
            if near:
                break
        if not near:
            _EMPTY[key] = time.time()
    return near[:k]
