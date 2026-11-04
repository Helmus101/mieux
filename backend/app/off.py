"""Open Food Facts client, isolated behind an interface so search endpoints can change without touching the app.

Open Food Facts rate-limits (about 10 searches and 100 product reads per minute per IP) and blocks clients that keep pushing: it answers 503, then 401.
So this client (1) spaces searches out, (2) keeps every answer on disk for days and serves it, even stale, when the service pushes back,
(3) stops calling for a while after a 503/429/401 instead of hammering, and (4) asks for as few searches as possible."""
import json
import os
import sqlite3
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import httpx

FIELDS = ("labels_tags,code,product_name,brands,image_front_small_url,nutriments,ingredients_text,additives_tags,allergens_tags,"
          "traces_tags,categories_tags,quantity,product_quantity,product_quantity_unit,ingredients_analysis_tags,nutriscore_grade,nutriscore_version,last_modified_t,nova_group,serving_quantity,countries_tags")
HEADERS = {"User-Agent": "Mieux/0.2 (prototype)"}
SEARCH_GAP = 7.0  # seconds between two searches (the limit is about 10 per minute)
FRESH = 7 * 86400  # a cached search is good for a week
LOCAL_PATH = os.environ.get("OFF_LOCAL", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "off_local.db"))
CACHE_PATH = os.environ.get("OFF_CACHE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "off_cache.db"))


class OFFError(Exception):
    pass


class NotFoodError(Exception):
    """Open Food Facts knows the barcode, but as another product type (book, cosmetic, pet food...)."""


class _Disk:
    """Tiny persistent key/value cache (own sqlite file, safe across threads and restarts)."""
    def __init__(self, path: str):
        self._lock = threading.Lock()
        try:
            self._c = sqlite3.connect(path, check_same_thread=False)
            self._c.execute("create table if not exists kv (k text primary key, ts real, v text)")
            self._c.commit()
        except sqlite3.Error:
            self._c = None

    def get(self, k: str):
        if not self._c:
            return None
        with self._lock:
            try:
                row = self._c.execute("select ts, v from kv where k=?", (k,)).fetchone()
            except sqlite3.Error:
                return None
        return (row[0], json.loads(row[1])) if row else None

    def set(self, k: str, v: Any) -> None:
        if not self._c:
            return
        with self._lock:
            try:
                self._c.execute("insert or replace into kv (k, ts, v) values (?,?,?)", (k, time.time(), json.dumps(v)))
                self._c.commit()
            except sqlite3.Error:
                pass


class _Local:
    """Mieux's own copy of the French Open Food Facts data (built by scripts/import_off_dump.py). No network, no rate limit, safe for many users.
    The file is swapped atomically by the monthly import; this class notices the new file and reopens it."""
    def __init__(self, path: str):
        self.path = path
        self.quick_path = os.environ.get("OFF_QUICK", os.path.join(os.path.dirname(path), "off_quick.db"))
        self._conn: Optional[sqlite3.Connection] = None
        self._sig = None
        self._quick = False
        self._lock = threading.Lock()

    def _c(self) -> Optional[sqlite3.Connection]:
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
                    self._quick = False
                    if os.path.exists(self.quick_path):
                        try:  # compact side index (scripts/build_quick_index.py), read-only, joined by code
                            self._conn.execute("attach database ? as quick", (f"file:{self.quick_path}?mode=ro",))
                            self._quick = True
                        except sqlite3.Error:
                            self._quick = False
                except sqlite3.Error:
                    self._conn = None
            return self._conn

    # -- whole-category selection over the compact side index ---------------------------------------------------------
    _QUICK_COLS = {"sugar", "salt", "protein", "fibre", "sat", "kcal", "grade"}

    def quick_available(self) -> bool:
        """True when the compact index is attached (built by scripts/build_quick_index.py)."""
        return bool(self._c() is not None and self._quick)

    def quick_candidates(self, tags: List[str], field: Optional[str] = None, low: bool = True,
                         required: tuple = (), ingredients: bool = False,
                         per_tag: int = 220, total: int = 260, window: int = 2000) -> List[str]:
        """Codes of the best candidates across these categories, chosen in SQL over the compact side table.

        For each category the `window` most scanned products are taken first (an index read, a few milliseconds even for
        14 000 products), then ordered by the nutrient the person cares about; the pooled result is topped up with the
        most scanned products, because the closest substitutes are usually the ones people actually buy. Ordering by the
        nutrient directly against the whole category means walking a million-row join (0.2-2 s), which the window avoids
        while still looking at two thousand products per category instead of one page. No product JSON is parsed here.
        """
        if not self.quick_available():
            return []
        field = field if field in self._QUICK_COLS else None
        cond = "".join(f" and q.{c} is not null" for c in required if c in self._QUICK_COLS)
        if ingredients:
            cond += " and q.ing = 1"
        order = ("q.grade is null, q.grade asc" if field == "grade" else f"q.{field} {'asc' if low else 'desc'}") if field else "c.scans desc"
        win = f"select code, scans from off_cat where tag=? order by scans desc limit {int(window)}"
        seen, out = set(), []

        def run(sql: str, args: tuple) -> None:
            for (code,) in self._q(sql, args) or []:
                if code not in seen:
                    seen.add(code)
                    out.append(code)

        for tag in tags:
            run(f"select q.code from ({win}) c join quick.quick q on q.code=c.code where 1=1{cond} order by {order} limit ?", (tag, per_tag))
            if len(out) >= total:
                return out[:total]
        for tag in tags:
            run(f"select q.code from ({win}) c join quick.quick q on q.code=c.code where 1=1{cond} order by c.scans desc limit ?", (tag, max(20, per_tag // 2)))
            if len(out) >= total:
                break
        return out[:total]

    def quick_products(self, codes: List[str]) -> List[Dict[str, Any]]:
        """Full records for these codes (only these are parsed): the expensive step happens on the final shortlist."""
        out: List[Dict[str, Any]] = []
        for i in range(0, len(codes), 400):
            chunk = codes[i:i + 400]
            rows = self._q("select data from off_products where code in (%s)" % ",".join("?" * len(chunk)), tuple(chunk))
            for (data,) in rows or []:
                try:
                    out.append(json.loads(data))
                except ValueError:
                    continue
        return out

    def _q(self, sql: str, args=()):
        c = self._c()
        if c is None:
            return None
        with self._lock:
            try:
                return c.execute(sql, args).fetchall()
            except sqlite3.Error:
                return None

    def available(self) -> bool:
        return bool(self._q("select 1 from off_products limit 1"))

    def product(self, code: str) -> Optional[Dict[str, Any]]:
        rows = self._q("select data from off_products where code=?", (code,))
        return json.loads(rows[0][0]) if rows else None

    def category(self, tag: str, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._q("select p.data from off_cat c join off_products p on p.code=c.code where c.tag=? order by c.scans desc limit ?", (tag, limit))
        return [json.loads(r[0]) for r in rows or []]

    def categories(self, tags: List[str], per_tag: int = 400, total: int = 1200) -> List[Dict[str, Any]]:
        """Raw records from several category tags (most specific first), most scanned first, without duplicates.
        One indexed query per tag; codes are de-duplicated before the JSON is parsed, so a product listed in two tags costs one parse."""
        seen: set = set()
        out: List[Dict[str, Any]] = []
        for tag in tags:
            rows = self._q("select p.code, p.data from off_cat c join off_products p on p.code=c.code where c.tag=? order by c.scans desc limit ?", (tag, per_tag))
            for code, data in rows or []:
                if code in seen:
                    continue
                seen.add(code)
                out.append(json.loads(data))
                if len(out) >= total:
                    return out
        return out

    def name(self, q: str, limit: int = 15) -> List[Dict[str, Any]]:
        import re
        toks = re.findall(r"\w+", q.lower())
        if not toks:
            return []
        match = " ".join(f'"{t}"' for t in toks[:6])
        rows = self._q("select p.data from off_names n join off_products p on p.code=n.code where off_names match ? order by p.scans desc limit ?", (match, limit))
        return [json.loads(r[0]) for r in rows or []]


class OFFClient:
    base = "https://world.openfoodfacts.org"

    def __init__(self, cache_path: Optional[str] = None):
        self.disk = _Disk(cache_path or CACHE_PATH)
        self.local = _Local(LOCAL_PATH)
        self._mem: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._last_search = 0.0
        self._blocked_until = 0.0
        self._fails = 0

    # -- transport -------------------------------------------------------------------------------------------------------------------
    def _wait_turn(self, search: bool) -> None:
        if not search:
            return
        with self._lock:
            wait = self._last_search + SEARCH_GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_search = time.monotonic()

    def _get(self, url: str, params: Dict[str, Any], tries: int = 2, search: bool = False, timeout: float = 20) -> Dict[str, Any]:
        if time.monotonic() < self._blocked_until:
            raise OFFError("Open Food Facts is pausing us (rate limit): using saved data")
        last: Optional[Exception] = None
        for i in range(tries):
            self._wait_turn(search)
            try:
                r = httpx.get(url, params=params, headers=HEADERS, timeout=timeout)
                if r.status_code in (200, 404) and r.text.startswith("{"):  # a JSON 404 is OFF's normal "no such product" answer, not a failure
                    self._fails = 0
                    return r.json()
                if r.status_code in (401, 403):  # blocked: stay away for a good while
                    self._blocked_until = time.monotonic() + 900
                    raise OFFError("Open Food Facts blocked this address for now")
                if r.status_code in (429, 503):
                    self._fails += 1
                    retry = r.headers.get("Retry-After")
                    pause = float(retry) if retry and retry.isdigit() else 20.0 * self._fails
                    if self._fails >= 2:
                        self._blocked_until = time.monotonic() + min(300.0, pause)
                        break
                    time.sleep(min(pause, 8.0))
                    continue
            except httpx.HTTPError as e:
                last = e
            time.sleep(0.6 * (i + 1))
        raise OFFError("Open Food Facts is not responding") from last

    # -- cached reads ----------------------------------------------------------------------------------------------------------------
    def _cached(self, key: str, fetch: Callable[[], Any], fresh: int = FRESH):
        """memory -> disk -> network. If the network fails, the last good answer (any age) is used; only if there is none does the error propagate."""
        now = time.time()
        hit = self._mem.get(key) or self.disk.get(key)
        if hit and now - hit[0] < fresh:
            self._mem[key] = hit
            return hit[1]
        try:
            out = fetch()
        except OFFError:
            if hit:
                return hit[1]
            raise
        self._mem[key] = (now, out)
        self.disk.set(key, out)
        return out

    def get_product(self, barcode: str) -> Optional[Dict[str, Any]]:
        hit = self.local.product(barcode)  # our own copy first: instant and unlimited
        if hit:
            return hit
        j = self._get(f"{self.base}/api/v2/product/{barcode}.json", {"fields": FIELDS}, 3, timeout=8)
        if j.get("status") == 0:
            if "different product type" in str(j.get("status_verbose", "")):
                raise NotFoodError(barcode)
            return None
        return j.get("product")

    def search_category(self, tag: str, size: int = 100, pages: int = 1) -> List[Dict[str, Any]]:
        """Products sold in France in the category, most scanned first (one request of up to 100 products: searches are the scarce resource)."""
        local = self.local.category(tag, size)
        if local:
            return local
        def go():
            j = self._get(f"{self.base}/api/v2/search", {"categories_tags": tag, "countries_tags": "en:france", "sort_by": "unique_scans_n", "page_size": size, "fields": FIELDS}, 2, search=True)
            return j.get("products") or []
        return self._cached(f"cat|{tag}|{size}", go)

    # -- whole-category selection (compact side index, see scripts/build_quick_index.py) --------------------------------
    def quick_available(self) -> bool:
        return self.local.quick_available()

    def quick_candidates(self, tags: List[str], field: Optional[str] = None, low: bool = True, required: tuple = (),
                         ingredients: bool = False, per_tag: int = 220, total: int = 260) -> List[str]:
        """Codes chosen across whole categories in SQL; empty when the compact index has not been built."""
        return self.local.quick_candidates(tags, field, low, required, ingredients, per_tag, total)

    def quick_products(self, codes: List[str]) -> List[Dict[str, Any]]:
        """Full records for the final shortlist only."""
        return self.local.quick_products(codes)

    def categories(self, tags: List[str], per_tag: int = 400, total: int = 1200) -> List[Dict[str, Any]]:
        """Several category tags at once: the local copy first (whole dataset, no rate limit). Without it, the first tag that
        answers over the network is used, so the caller still gets a pool."""
        got = self.local.categories(tags, per_tag, total)
        if got:
            return got
        for tag in tags:
            try:
                return self.search_category(tag, min(per_tag, 100))
            except OFFError:
                continue
        return []

    def search_name(self, q: str) -> List[Dict[str, Any]]:
        local = self.local.name(q)
        if local:
            return local
        def go():
            j = self._get(f"{self.base}/cgi/search.pl", {"search_simple": 1, "action": "process", "json": 1, "page_size": 15, "fields": FIELDS, "search_terms": q, "tagtype_0": "countries", "tag_contains_0": "contains", "tag_0": "france"}, 2, search=True)
            return j.get("products") or []
        return self._cached(f"name|{q}", go)
