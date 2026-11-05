"""Which French chains stock a product, and how far the nearest branch is.
Stocking evidence is never invented: a chain is listed only if (a) a community price was seen in one of its shops, or (b) the product carries
that chain's own brand. Branch locations come from OpenStreetMap (Overpass), used once per request, nothing stored."""
import json
import math
import re
import subprocess
import time
from typing import Any, Dict, List, Optional

import httpx

from . import market

# canonical chain -> regex matched against OSM brand/name and Open Prices shop names
CHAINS: Dict[str, str] = {
    "Carrefour": r"carrefour", "Auchan": r"auchan", "E.Leclerc": r"leclerc", "Intermarché": r"intermarch", "Lidl": r"\blidl\b", "Aldi": r"\baldi\b",
    "Monoprix": r"monoprix", "Franprix": r"franprix", "Casino": r"casino|petit casino|spar\b", "Super U": r"super u|hyper u|u express|syst[eè]me u|\bu\b",
    "Picard": r"picard", "Biocoop": r"biocoop", "Naturalia": r"naturalia", "La Vie Claire": r"vie claire", "Grand Frais": r"grand frais", "Cora": r"\bcora\b", "Match": r"\bmatch\b",
    # United States (Aldi and Lidl above also trade there)
    "Walmart": r"wal-?mart", "Kroger": r"\bkroger\b", "Costco": r"costco", "Target": r"\btarget\b", "Albertsons": r"albertsons", "Safeway": r"safeway", "Publix": r"publix",
    "Whole Foods": r"whole foods", "Trader Joe's": r"trader joe", "H-E-B": r"\bh-?e-?b\b", "Wegmans": r"wegmans", "Sprouts": r"sprouts", "Food Lion": r"food lion",
    "Stop & Shop": r"stop ?(&|and) ?shop", "Meijer": r"meijer", "Sam's Club": r"sam'?s club", "BJ's": r"\bbj'?s\b", "Hy-Vee": r"hy-?vee", "ShopRite": r"shop-?rite",
    "Harris Teeter": r"harris teeter", "Winn-Dixie": r"winn-?dixie",
}
# plain words for the Overpass brand filter
TOKENS: Dict[str, str] = {"Carrefour": "Carrefour", "Auchan": "Auchan", "E.Leclerc": "Leclerc", "Intermarché": "Intermarch", "Lidl": "Lidl", "Aldi": "Aldi", "Monoprix": "Monoprix",
                          "Franprix": "Franprix", "Casino": "Casino", "Super U": "Super U|Hyper U|U Express|Marché U", "Picard": "Picard", "Biocoop": "Biocoop", "Naturalia": "Naturalia", "La Vie Claire": "La Vie Claire",
                          "Grand Frais": "Grand Frais", "Cora": "Cora", "Match": "Match",
                          "Walmart": "Walmart", "Kroger": "Kroger", "Costco": "Costco", "Target": "Target", "Albertsons": "Albertsons", "Safeway": "Safeway", "Publix": "Publix", "Whole Foods": "Whole Foods",
                          "Trader Joe's": "Trader Joe", "H-E-B": "H-E-B", "Wegmans": "Wegmans", "Sprouts": "Sprouts", "Food Lion": "Food Lion", "Stop & Shop": "Stop & Shop", "Meijer": "Meijer",
                          "Sam's Club": "Sam's Club", "BJ's": "BJ's", "Hy-Vee": "Hy-Vee", "ShopRite": "ShopRite", "Harris Teeter": "Harris Teeter", "Winn-Dixie": "Winn-Dixie"}
# what to type in the OpenStreetMap search box (the regex tokens above are for matching, not searching)
QUERY: Dict[str, str] = {"E.Leclerc": "Leclerc", "Intermarché": "Intermarché", "Super U": "Super U", "Grand Frais": "Grand Frais"}
# own brands that only a chain sells (lower-case brand fragments)
OWN_BRANDS: Dict[str, str] = {
    "auchan": "Auchan", "carrefour": "Carrefour", "marque repère": "E.Leclerc", "bio village": "E.Leclerc", "eco+": "E.Leclerc", "chabrior": "Intermarché",
    "paturages": "Intermarché", "pâturages": "Intermarché", "top budget": "Intermarché", "marque u": "Super U", "u bio": "Super U", "u tout petits": "Super U",
    "milbona": "Lidl", "dulano": "Lidl", "freeway": "Lidl", "mamia": "Aldi", "monoprix": "Monoprix", "franprix": "Franprix", "casino": "Casino", "picard": "Picard",
    "biocoop": "Biocoop", "cora": "Cora", "naturalia": "Naturalia", "la vie claire": "La Vie Claire",
    # United States: store brands only that chain sells
    "great value": "Walmart", "marketside": "Walmart", "kirkland": "Costco", "good & gather": "Target", "good and gather": "Target", "market pantry": "Target", "favorite day": "Target",
    "simple truth": "Kroger", "private selection": "Kroger", "kroger": "Kroger", "trader joe": "Trader Joe's", "whole foods market": "Whole Foods", "365 by": "Whole Foods",
    "o organics": "Albertsons", "signature select": "Safeway", "signature farms": "Safeway", "publix": "Publix", "greenwise": "Publix", "h-e-b": "H-E-B", "wegmans": "Wegmans",
    "sprouts": "Sprouts", "food lion": "Food Lion", "nature's promise": "Stop & Shop", "meijer": "Meijer", "member's mark": "Sam's Club", "wellsley farms": "BJ's", "hy-vee": "Hy-Vee",
    "harris teeter": "Harris Teeter", "winn-dixie": "Winn-Dixie", "simply nature": "Aldi", "specially selected": "Aldi", "friendly farms": "Aldi", "preferred selection": "Lidl",
}
_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_cache: Dict[Any, Any] = {}


def canon(text: Optional[str]) -> Optional[str]:
    t = (text or "").lower()
    for name, rx in CHAINS.items():
        if re.search(rx, t):
            return name
    return None


def own_brand_chain(brand: Optional[str]) -> Optional[str]:
    b = (brand or "").lower()
    for frag, chain in OWN_BRANDS.items():
        if frag in b:
            return chain
    return None


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _get_json(url: str, params: Dict[str, Any]) -> Any:
    """GET json. Some Python builds (old LibreSSL) cannot handshake with OSM servers, so fall back to the system curl."""
    try:
        r = httpx.get(url, params=params, headers={"User-Agent": "Mieux/0.2 (prototype)"}, timeout=12)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        cmd = ["curl", "-s", "-m", "12", "-G", "-A", "Mieux/0.2 (prototype)", url] + [x for k, v in params.items() for x in ("--data-urlencode", f"{k}={v}")]
        return json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout)


def nearest_branches(lat: float, lon: float, chains: List[str], radius_km: int = 15) -> Dict[str, Dict[str, Any]]:
    """Nearest shop per chain within ~radius_km, from OpenStreetMap's Nominatim search (one polite request per chain). {} if unreachable."""
    chains = [c for c in chains if c in CHAINS][:6]
    radius_km = float(radius_km)
    key = (round(lat, 2), round(lon, 2), tuple(sorted(chains)), radius_km)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    out: Dict[str, Dict[str, Any]] = {}
    steps = sorted({min(radius_km, r) for r in (1.5, 4, 10, radius_km)})  # widen the box only for chains not found yet, so the closest branch wins and urban lookups stay fast
    pending = list(chains)
    first = True
    for r_km in steps:
        dlat = r_km / 111.0
        dlon = r_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
        for ch in list(pending):
            if not first:
                time.sleep(1.0)  # Nominatim usage policy: at most one request per second
            first = False
            try:
                res = _get_json(_NOMINATIM, {"q": QUERY.get(ch, ch), "format": "jsonv2", "limit": 40, "addressdetails": 1, "countrycodes": market.current().lower(),
                                             "viewbox": f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}", "bounded": 1})
            except Exception:
                continue
            for el in res or []:
                if canon(el.get("name") or el.get("display_name", "").split(",")[0]) != ch:
                    continue
                la, lo = float(el["lat"]), float(el["lon"])
                d = haversine_km(lat, lon, la, lo)
                if d > r_km * 1.01:
                    continue
                if ch not in out or d < out[ch]["distance_km"]:
                    a_ = el.get("address") or {}
                    addr = " ".join(x for x in [a_.get("house_number"), a_.get("road")] if x)
                    out[ch] = {"name": el.get("name") or ch, "distance_km": round(d, 2), "lat": la, "lon": lo,
                               "address": ", ".join(x for x in [addr, a_.get("city") or a_.get("town") or a_.get("village")] if x) or None, "hours": None}
            if ch in out:
                pending.remove(ch)
        if not pending:
            break
    if out:
        _cache[key] = (time.time(), out)
    return out
