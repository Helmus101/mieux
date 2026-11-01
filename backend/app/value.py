"""Value-for-money logic. Prices are never invented: every price point carries its source and date, and a saving is
claimed only when both products have a dated price and a known pack size in the same unit (g or ml)."""
import json
import math
import os
import sqlite3
import threading
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

FRESH_DAYS = 180
_UNITS = {"g": ("g", 1.0), "kg": ("g", 1000.0), "mg": ("g", 0.001), "ml": ("ml", 1.0), "cl": ("ml", 10.0), "l": ("ml", 1000.0), "dl": ("ml", 100.0)}


def parse_quantity(text: Optional[str], numeric: Any = None, unit: Optional[str] = None) -> Optional[Tuple[float, str]]:
    """Returns (amount, 'g'|'ml') or None. Handles '375 g', '1,5 l', '6 x 125 g'."""
    if numeric not in (None, ""):
        try:
            v = float(numeric)
            u = (unit or "g").lower()
            if v > 0 and u in _UNITS:
                return v * _UNITS[u][1], _UNITS[u][0]
        except (TypeError, ValueError):
            pass
    if not text:
        return None
    t = text.lower().replace(",", ".")
    m = re.search(r"(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(kg|g|mg|ml|cl|dl|l)\b", t)
    if m:
        n, a, u = int(m.group(1)), float(m.group(2)), m.group(3)
        return n * a * _UNITS[u][1], _UNITS[u][0]
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|mg|ml|cl|dl|l)\b", t)
    if m:
        return float(m.group(1)) * _UNITS[m.group(2)][1], _UNITS[m.group(2)][0]
    return None


def per100(pack_cents: int, qty: Tuple[float, str]) -> float:
    return pack_cents / qty[0] * 100.0


def fresh(d: Optional[str], today: Optional[date] = None) -> bool:
    try:
        return (today or date.today()) - datetime.strptime((d or "")[:10], "%Y-%m-%d").date() <= timedelta(days=FRESH_DAYS)
    except ValueError:
        return False


def age_days(d: Optional[str], today: Optional[date] = None) -> Optional[int]:
    try:
        return ((today or date.today()) - datetime.strptime((d or "")[:10], "%Y-%m-%d").date()).days
    except ValueError:
        return None


class FX:
    """Currency -> EUR using the ECB reference rates (frankfurter.dev), cached 12 h. None if unavailable: such prices are skipped, never guessed."""
    def __init__(self):
        self._c: Dict[str, Tuple[float, Optional[float]]] = {}

    def to_eur(self, cur: str) -> Optional[float]:
        if cur == "EUR":
            return 1.0
        hit = self._c.get(cur)
        if hit and time.time() - hit[0] < 43200:
            return hit[1]
        rate = None
        try:
            r = httpx.get("https://api.frankfurter.dev/v1/latest", params={"base": cur, "symbols": "EUR"}, timeout=8, follow_redirects=True)
            if r.status_code == 200:
                rate = float(r.json()["rates"]["EUR"])
        except (httpx.HTTPError, ValueError, KeyError):
            rate = None
        self._c[cur] = (time.time(), rate)
        return rate


class _LocalPrices:
    """Mieux's own copy of the French Open Prices data (scripts/import_prices_dump.py): no network, no rate limit. Reopened when the file is replaced."""
    def __init__(self, path: str):
        self.path = path
        self._conn = None
        self._sig = None
        self._lock = threading.Lock()

    def _c(self):
        try:
            st = os.stat(self.path)
        except OSError:
            return None
        sig = (st.st_mtime, st.st_size)
        with self._lock:
            if self._conn is None or sig != self._sig:
                try:
                    self._conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
                    self._sig = sig
                except sqlite3.Error:
                    self._conn = None
            return self._conn

    def available(self) -> bool:
        return self._c() is not None

    def items(self, code: str) -> List[Dict[str, Any]]:
        c = self._c()
        if c is None:
            return []
        with self._lock:
            try:
                rows = c.execute("select data from op_items where code=? order by date desc", (code,)).fetchall()
            except sqlite3.Error:
                return []
        return [json.loads(r[0]) for r in rows]


class OpenPricesClient:
    """Community price observations (Open Food Facts / Open Prices). Kept separate from the user's own receipts."""
    base = "https://prices.openfoodfacts.org/api/v1/prices"

    def __init__(self, local_path: Optional[str] = None):
        self.local = _LocalPrices(local_path or os.environ.get("OP_LOCAL", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "op_local.db")))
        self._raw: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self.fx = FX()

    def prefetch(self, codes: List[str], pages: int = 4) -> None:
        """Fetch the observations of many products in a few requests (product_code__in) and fill the per-product cache. Not needed with the local copy."""
        if self.local.available():
            return
        todo = [c for c in dict.fromkeys(codes) if not (self._raw.get(c) and time.time() - self._raw[c][0] < 3600)]
        for i in range(0, len(todo), 25):
            chunk = todo[i:i + 25]
            got: Dict[str, List[Dict[str, Any]]] = {c: [] for c in chunk}
            ok = True
            for page in range(1, pages + 1):
                try:
                    r = httpx.get(self.base, params={"product_code__in": ",".join(chunk), "order_by": "-date", "size": 100, "page": page},
                                  headers={"User-Agent": "Mieux/0.2 (prototype)"}, timeout=12)
                    if r.status_code != 200:
                        ok = False
                        break
                    items = r.json().get("items", [])
                except (httpx.HTTPError, ValueError):
                    ok = False
                    break
                for it in items:
                    got.setdefault(str(it.get("product_code")), []).append(it)
                if len(items) < 100:
                    break
            if ok:
                for c, its in got.items():
                    self._raw[c] = (time.time(), its)

    def seen_in_france(self, barcode: str) -> bool:
        """A community price was recorded for this exact barcode in a shop located in France."""
        return any(((it.get("location") or {}).get("osm_address_country_code") or "").upper() == "FR" for it in self._items(barcode))

    def _items(self, barcode: str) -> List[Dict[str, Any]]:
        if self.local.available():  # our own copy of the French prices: instant and unlimited
            return self.local.items(barcode)
        hit = self._raw.get(barcode)
        if hit and time.time() - hit[0] < 3600:
            return hit[1]
        items: List[Dict[str, Any]] = []
        try:
            r = httpx.get(self.base, params={"product_code": barcode, "order_by": "-date", "size": 100},
                          headers={"User-Agent": "Mieux/0.2 (prototype)"}, timeout=8)
            if r.status_code == 200:
                items = r.json().get("items", [])
        except (httpx.HTTPError, ValueError):
            items = []
        self._raw[barcode] = (time.time(), items)
        return items

    @staticmethod
    def _per100(it: Dict[str, Any], qty: Optional[Tuple[float, str]]) -> Optional[float]:
        """Price per 100 g/ml in the observation's OWN currency, in minor units (cents of that currency)."""
        p, per = it.get("price"), (it.get("price_per") or "").upper()
        if p is None:
            return None
        if per == "KILOGRAM":
            return float(p) * 10.0
        if qty and per in ("", "UNIT"):
            return per100(round(float(p) * 100), qty)
        return None

    def latest(self, barcode: str, qty: Optional[Tuple[float, str]], max_age_days: int = 730, country: str = "FR", only: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """The price of the product in France: the AVERAGE of the per-chain averages of recent Open Prices observations (EUR, converted at the ECB rate).
        Prices seen outside France are ignored. 'stale' when nothing is newer than FRESH_DAYS."""
        if not qty:
            return None
        chains = [c for c in self.chain_summary(barcode, qty, only) if c["per100_cents"] is not None]
        if not chains:
            return None
        avg = sum(c["per100_cents"] for c in chains) / len(chains)
        n_obs = sum(c["observations"] for c in chains)
        newest = max(c["newest"] for c in chains)
        packs = [c["pack_cents"] for c in chains if c["pack_cents"] is not None]
        return {"source": "open_prices", "per100_cents": round(avg, 2), "date": newest, "where": None, "currency": "EUR", "price_native": None, "fx": 1.0,
                "stale": all(c["stale"] for c in chains), "pack_cents": round(sum(packs) / len(packs)) if packs else None, "n_observations": n_obs, "n_chains": len(chains)}

    def _observations(self, barcode: str, qty, max_age_days: int = 1095, country: str = "FR"):
        """Open Prices observations made in French shops, with a canonical chain, a price per 100 g/ml in EUR (when the pack size is known) and an age."""
        from . import chains as ch
        out = []
        for it in self._items(barcode):
            loc = it.get("location") or {}
            if (loc.get("osm_address_country_code") or "").upper() != country:
                continue
            age = age_days(it.get("date"))
            if age is None or age > max_age_days:
                continue
            chain = ch.canon(loc.get("osm_brand")) or ch.canon(loc.get("osm_name"))
            rate = self.fx.to_eur((it.get("currency") or "EUR").upper())
            native = self._per100(it, qty) if qty else None
            unit = (it.get("price_per") or "").upper() in ("", "UNIT")
            out.append({"chain": chain, "shop": loc.get("id") or loc.get("osm_id"), "age": age, "date": it["date"][:10],
                        "per100": None if (native is None or rate is None) else native * rate, "pack": float(it["price"]) * 100 * rate if (unit and rate) else None})
        return out

    def chain_summary(self, barcode: str, qty: Optional[Tuple[float, str]], only: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Per chain seen in France: number of observations and shops, newest date and the AVERAGE price per 100 g/ml (recent observations first,
        outliers beyond 50 % of the chain median dropped). One sighting in one shop is taken to mean the chain lists the product."""
        by: Dict[str, List[Dict[str, Any]]] = {}
        for o in self._observations(barcode, qty):
            if only and o["chain"] not in only:
                continue
            by.setdefault(o["chain"] or "", []).append(o)  # shops that are no known chain still count for the price, never as a chain listing
        res = []
        for chain, obs in by.items():
            recent = [o for o in obs if o["age"] <= 365 and o["per100"] is not None] or [o for o in obs if o["per100"] is not None]
            vals = sorted(o["per100"] for o in recent)
            if vals:
                med = vals[len(vals) // 2]
                kept = [v for v in vals if 0.5 * med <= v <= 1.5 * med] or vals
                avg = sum(kept) / len(kept)
            else:
                avg = None
            packs = [o["pack"] for o in obs if o["pack"] is not None and o["age"] <= 365] or [o["pack"] for o in obs if o["pack"] is not None]  # older packs still show, marked stale
            res.append({"chain": chain or None, "observations": len(obs), "shops": len({o["shop"] for o in obs if o["shop"] is not None}) or 1, "newest": max(o["date"] for o in obs),
                        "per100_cents": None if avg is None else round(avg, 1), "pack_cents": round(sum(packs) / len(packs)) if packs else None,
                        "stale": all(o["age"] > FRESH_DAYS for o in obs)})
        return sorted(res, key=lambda r: (r["per100_cents"] is None, r["per100_cents"] or 0))

    def stores(self, barcode: str, qty: Optional[Tuple[float, str]], lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
        """Latest fresh price per shop within radius_km of (lat, lon), cheapest first."""
        best: Dict[Any, Dict[str, Any]] = {}
        for it in self._items(barcode):
            loc = it.get("location") or {}
            if not fresh(it.get("date")) or loc.get("osm_lat") is None or loc.get("osm_lon") is None:
                continue
            d = haversine_km(lat, lon, float(loc["osm_lat"]), float(loc["osm_lon"]))
            p100 = self._per100(it, qty)
            if d > radius_km or p100 is None:
                continue
            key = loc.get("id") or loc.get("osm_id")
            if key in best:  # items are newest first: keep the newest per shop
                continue
            unit = (it.get("price_per") or "").upper() in ("", "UNIT")
            best[key] = {"store": loc.get("osm_brand") or loc.get("osm_name") or "?", "name": loc.get("osm_name"), "city": loc.get("osm_address_city"),
                         "per100_cents": round(p100, 1), "pack_cents": round(float(it["price"]) * 100) if unit else None,
                         "date": it["date"][:10], "distance_km": round(d, 1), "source": "open_prices",
                         "lat": float(loc["osm_lat"]), "lon": float(loc["osm_lon"])}
        return sorted(best.values(), key=lambda x: x["per100_cents"])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def price_point(product: Dict[str, Any], own: Optional[Dict[str, Any]], community: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prefer the user's own recorded price; fall back to a fresh community observation. Always label the source."""
    q = product.get("quantity")
    if own and q and fresh(own.get("date")):
        return {"source": "your_receipt", "per100_cents": per100(own["unit_price_cents"], (q["amount"], q["unit"])), "date": own["date"], "where": own.get("retailer")}
    return community
