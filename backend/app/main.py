import contextvars
import hashlib
import re
import urllib.parse
import secrets
from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError
import json
import logging
import os
from typing import Any, Dict, Iterator, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def _load_dotenv() -> None:
    """Tiny .env reader (KEY=value lines) so secrets live in backend/.env, never in client code. Real env vars win."""
    path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()
from . import chains as _chains, value_index, budget as bud, db, engine, estimate, explain as exp, market, receipts, retail, score, taxonomy, value
from .i18n import tr
from concurrent.futures import ThreadPoolExecutor
from .off import OFFClient, OFFError, NotFoodError
from .products import normalize, SCHEMA_VERSION
from .auth import get_user_or_anonymous, create_access_token

# Structured logging (basic setup for now)
import logging
import time
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Simple LRU cache for product data (reduce DB hits)
from collections import OrderedDict
class SimpleCache:
    def __init__(self, max_size=500):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

product_cache = SimpleCache(max_size=500)

# Batch visit logging to reduce DB write contention (write every 10 visits or 30 seconds)
from threading import Lock, Timer
class VisitBatcher:
    def __init__(self, batch_size=10, flush_interval=30):
        self.batch = []
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.lock = Lock()
        self.timer = None
        self.app_state = None

    def set_app_state(self, app_state):
        """Set reference to app.state after app is created."""
        self.app_state = app_state

    def add(self, day: str, surface: str, visitor: str, person: Optional[str], referrer: Optional[str]):
        with self.lock:
            self.batch.append((day, surface, visitor, person, referrer))
            if len(self.batch) >= self.batch_size:
                self._flush_sync()
            elif self.timer is None:
                self.timer = Timer(self.flush_interval, self._flush_async)
                self.timer.daemon = True
                self.timer.start()

    def flush(self):
        """Synchronous flush for testing."""
        with self.lock:
            if self.batch:
                batch = self.batch[:]
                self.batch.clear()
                if self.timer:
                    self.timer.cancel()
                    self.timer = None
                self._write_batch(batch)

    def _flush_sync(self):
        """Flush without rescheduling the timer."""
        batch = self.batch[:]
        self.batch.clear()
        if self.timer:
            self.timer.cancel()
            self.timer = None
        import threading
        threading.Thread(target=self._write_batch, args=(batch,), daemon=True).start()

    def _flush_async(self):
        """Flush on timer expiry."""
        with self.lock:
            if self.batch:
                batch = self.batch[:]
                self.batch.clear()
                self.timer = None
                import threading
                threading.Thread(target=self._write_batch, args=(batch,), daemon=True).start()

    def _write_batch(self, batch):
        """Write batch to database (background thread)."""
        if not self.app_state:
            return
        try:
            with self.app_state.sessions() as s:
                for day, surface, visitor, person, referrer in batch:
                    try:
                        existing = s.query(db.Visit).filter_by(day=day, surface=surface, visitor=visitor).first()
                        if not existing and not (person and s.query(db.Visit).filter_by(day=day, surface=surface, person=person).first()):
                            s.add(db.Visit(day=day, surface=surface, visitor=visitor, person=person, referrer=referrer))
                    except IntegrityError:
                        pass
                s.commit()
        except Exception as e:
            logger.error(f"Failed to write visit batch: {e}")

visit_batcher = VisitBatcher(batch_size=10, flush_interval=30)

# Rate limiting
def client_ip(request: Request) -> str:
    """Behind Fly's proxy every request comes from the proxy: rate limit per real client address instead."""
    return request.headers.get("fly-client-ip") or get_remote_address(request)


limiter = Limiter(key_func=client_ip)
app = FastAPI(title="Mieux API", version="0.2")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8010").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=800)


_IDEM: Dict[str, Any] = {}   # (session, path, key) -> (expires, status, body, content-type)


@app.middleware("http")
async def idempotency(request, call_next):
    """A POST that repeats an Idempotency-Key within two minutes gets the first successful answer back instead of running again."""
    key = request.headers.get("idempotency-key")
    if request.method != "POST" or not key or len(key) > 80:
        return await call_next(request)
    from starlette.responses import Response
    import time as _t
    k = f"{request.headers.get('x-session-id', '')}|{request.url.path}|{key}"
    now = _t.time()
    for old in [x for x, v in _IDEM.items() if v[0] < now]:
        _IDEM.pop(old, None)
    hit = _IDEM.get(k)
    if hit:
        return Response(content=hit[2], status_code=hit[1], media_type=hit[3], headers={"Idempotent-Replay": "true"})
    resp = await call_next(request)
    if resp.status_code < 400 and len(_IDEM) < 2000:
        body = b"".join([c async for c in resp.body_iterator])
        _IDEM[k] = (now + 120, resp.status_code, body, resp.media_type or "application/json")
        return Response(content=body, status_code=resp.status_code, media_type=resp.media_type, headers=dict(resp.headers))
    return resp


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    return resp


# Request logging middleware for performance monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    REQ_PREFS.set(None)
    market.set_current(request.headers.get("x-country"))  # FR unless the app says it is a US shopper
    raw = request.headers.get("x-prefs")
    if raw and len(raw) < 2000:
        try:
            REQ_PREFS.set(Prefs(**json.loads(urllib.parse.unquote(raw))))
        except Exception:
            pass
    response = await call_next(request)
    duration = (time.time() - start) * 1000  # milliseconds
    logger.info(f"req {request.method} {request.url.path} status={response.status_code} ms={duration:.0f}")
    return response

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# One local Open Food Facts copy per market (scripts/import_off_dump.py, OFF_COUNTRY); app.state.off forwards to the request's market.
app.state.off = market.PerMarket({
    "FR": OFFClient(),
    "US": OFFClient(cache_path=os.environ.get("OFF_CACHE_US", os.path.join(_HERE, "off_cache_us.db")), local_path=os.environ.get("OFF_LOCAL_US", os.path.join(_HERE, "off_local_us.db")),
                    quick_path=os.environ.get("OFF_QUICK_US", os.path.join(_HERE, "off_quick_us.db")), country="united-states"),
})
app.state.prices = market.PerMarket({
    "FR": value.OpenPricesClient(),
    "US": value.OpenPricesClient(local_path=os.environ.get("OP_LOCAL_US", os.path.join(_HERE, "op_local_us.db")), country="US", base="USD"),
})
app.state.llm = None  # no language model: explanations are always built from the computed facts
app.state.sessions = db.make_session_factory()
visit_batcher.set_app_state(app.state)  # Enable background visit batching
with app.state.sessions() as _s:
    retail.seed(_s)
WEB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "index.html"))


def lang_of(x_lang: Optional[str] = Header(None)) -> str:
    return "en" if (x_lang or "fr").lower().startswith("en") else "fr"


def get_db() -> Iterator[Session]:
    s = app.state.sessions()
    try:
        yield s
    finally:
        s.close()


def user(
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
    s: Session = Depends(get_db)
) -> str:
    """Get user ID from JWT token or anonymous session.

    Supports both authenticated users (via JWT) and anonymous sessions (via X-Session-Id).
    Accounts are optional so scanning is never blocked.
    """
    try:
        user_obj, session_id = get_user_or_anonymous(authorization, x_session_id)
    except HTTPException:
        # If neither auth nor session provided, fall back to session-only
        if x_session_id and len(x_session_id) >= 8:
            user_obj, session_id = None, x_session_id
        else:
            raise

    if user_obj:
        user_id = user_obj["id"]
        # Create or update user record with supabase_id if present
        if not s.get(db.User, user_id):
            try:
                s.add(db.User(id=user_id, supabase_id=user_obj.get("supabase_id")))
                s.commit()
            except IntegrityError:  # a parallel first request created it
                s.rollback()
        return user_id
    else:
        # Anonymous session
        if not s.get(db.User, session_id):
            try:
                s.add(db.User(id=session_id))
                s.commit()
            except IntegrityError:  # a parallel first request created it
                s.rollback()
        return session_id


# ---- models
class Prefs(BaseModel):
    diet: str = "omnivore"
    priorities: List[str] = []
    allergens: List[str] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str


class Loc(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_km: float = Field(15, gt=0, le=100)


class GeoReq(BaseModel):
    postcode: Optional[str] = None
    query: Optional[str] = None


class AltReq(BaseModel):
    approximate: bool = False  # opt-in: fill missing prices with clearly-labelled estimates (default: real data only)
    location: Optional[Loc] = None
    priorities: List[str] = Field(min_length=1)
    category_mode: str = "similar"  # similar | any
    price_constraint: str = "any"
    excluded_allergens: Optional[List[str]] = None
    diet: Optional[str] = None
    limit: int = Field(20, ge=1, le=20)
    chains: List[str] = []  # chain ids the user shops at (empty = all)
    nearby_only: bool = False  # with a location: keep only products listed at a chain that has a branch within the radius (and within the user's chains)
    strict_additives: bool = True  # strict mode (40 % nutrition + 25 % additives + 25 % ingredient quality, every additive concern one level higher)
    same_size: bool = False  # only products whose pack size is within half to double of the scanned one
    substitution_max: int = Field(4, ge=1, le=4)  # 1 almost identical ... 4 broader alternative


class CmpReq(BaseModel):
    approximate: bool = False
    product_ids: List[str] = Field(min_length=2, max_length=4)


class OcrLine(BaseModel):
    text: str
    confidence: float = 0.9
    position: int = 0


class PreviewReq(BaseModel):
    locale: str = "fr-FR"
    lines: List[OcrLine]


class ConfItem(BaseModel):
    raw_description: str
    quantity: int = 1
    unit_price_cents: int
    line_total_cents: int
    is_discount: bool = False
    matched_product_id: Optional[str] = None
    match_confidence: Optional[float] = None
    extraction_confidence: float = 1.0


class ConfirmReq(BaseModel):
    retailer: Optional[str] = None
    purchase_date: Optional[str] = None
    total_cents: Optional[int] = None
    items: List[ConfItem] = Field(min_length=1)
    allow_duplicate: bool = False


# ---- helpers
def _sold_here(p: Dict[str, Any]) -> Optional[bool]:
    """Is the product listed as sold in this request's market? None when its countries are unknown. Recomputed on every request: the cached row was normalised for whichever market asked first."""
    cs = p.get("countries") or []
    return None if not cs else market.MARKETS[market.current()] in cs


def load_product(s: Session, barcode: str, refresh: bool = False) -> Dict[str, Any]:
    p = _load_product(s, barcode, refresh)
    here = _sold_here(p)
    if here != p.get("soldInFrance") or (market.current() != "FR" and p.get("frEvidence")):
        p = {**p, "soldInFrance": here, "frEvidence": p.get("frEvidence") if market.current() == "FR" else None}
    return p


def _load_product(s: Session, barcode: str, refresh: bool = False) -> Dict[str, Any]:
    if not re.fullmatch(r"\d{1,14}", barcode or ""):
        raise HTTPException(400, "Invalid barcode: digits only")
    row = s.get(db.Product, barcode)
    cached = json.loads(row.data) if row else None
    if cached and cached.get('_v') != SCHEMA_VERSION:
        refresh = True  # cached with an older shape: refetch
    if row and not refresh:
        return cached
    try:
        raw = app.state.off.get_product(barcode)
    except NotFoodError:
        raise HTTPException(404, "not_food")
    except OFFError as e:
        if row:  # offline: serve cache with its date
            d = cached
            d["served_from_cache"] = True
            return d
        raise HTTPException(503, "Product service is busy, please retry")  # transient: never say "not found" when we simply could not ask
    if raw is None:
        raise HTTPException(404, "Product not found")
    p = normalize(raw)
    if row:
        row.data, row.name, row.brand, row.category, row.fetched_at = json.dumps(p), p["name"], p["brand"], p["category"], db.now()
    else:
        s.add(db.Product(id=p["id"], name=p["name"], brand=p["brand"], category=p["category"], data=json.dumps(p)))
    s.add(db.ProductSnapshot(product_id=p["id"], source_updated_at=p["dataQuality"]["lastUpdatedAt"], raw=json.dumps(raw)[:200000]))
    s.commit()
    return p


def _ctx_map(ex: ThreadPoolExecutor, fn, items) -> list:
    """ThreadPoolExecutor.map, but every call runs in a copy of the caller's context, so worker threads see the request's market and preferences."""
    items = list(items)
    ctxs = [contextvars.copy_context() for _ in items]
    return list(ex.map(lambda cx_x: cx_x[0].run(fn, cx_x[1]), zip(ctxs, items)))


REQ_PREFS: "contextvars.ContextVar[Optional[Prefs]]" = contextvars.ContextVar("req_prefs", default=None)


def is_account(s: Session, uid: str) -> bool:
    """A signed-in (Supabase) person: nothing about them is stored except a scan counter."""
    row = s.get(db.User, uid)
    return bool(row and row.supabase_id)


def prefs_of(s: Session, uid: str) -> Prefs:
    sent = REQ_PREFS.get()
    if sent is not None and is_account(s, uid):  # an account sends its restrictions with each request instead of saving them
        return sent
    r = s.get(db.Preference, uid)
    return Prefs(diet=r.diet, priorities=json.loads(r.priorities), allergens=json.loads(r.allergens)) if r else Prefs()


# ---- endpoints
@app.get("/v1/health")
def health():
    return {"ok": True}


# ---- usage: how many people actually use Mieux (anonymous, cookie-free)
class VisitIn(BaseModel):
    surface: str = Field(pattern="^(landing|app)$")


def _visitor(request: Request) -> str:
    """Daily-rotating hash of IP + browser. Raw values are never stored, so nobody can be followed across days."""
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (request.client.host if request.client else "")
    ua = request.headers.get("user-agent", "")[:400]
    salt = os.getenv("USAGE_SALT") or os.getenv("JWT_SECRET_KEY")
    if not salt:
        raise RuntimeError("USAGE_SALT or JWT_SECRET_KEY environment variable must be set")
    return hashlib.sha256(f"{date.today().isoformat()}|{ip}|{ua}|{salt}".encode()).hexdigest()[:32]


def _person(request: Request) -> Optional[str]:
    """Stable anonymous id, so distinct people can be counted across days. It is a hash of the id the browser already
    keeps to store scans — never the id itself, never an IP — and it is absent until that id exists."""
    sid = (request.headers.get("x-session-id") or "").strip()
    if len(sid) < 8:
        return None
    salt = os.getenv("USAGE_SALT") or os.getenv("JWT_SECRET_KEY")
    if not salt:
        raise RuntimeError("USAGE_SALT or JWT_SECRET_KEY environment variable must be set")
    return hashlib.sha256(f"person|{sid}|{salt}".encode()).hexdigest()[:32]


def _referrer(request: Request) -> str:
    ref = request.headers.get("referer") or ""
    if not ref:
        return "direct"
    return "internal" if ref.startswith(str(request.base_url).rstrip("/")) else "external"


@app.post("/v1/usage/visit")
@limiter.limit("60/minute")
def usage_visit(request: Request, body: VisitIn, s: Session = Depends(get_db)):
    """Batch visit logging to reduce DB write contention at scale. Writes in background (max 30s delay).
    Tracks visitor counts, surface (landing page vs app), and person identifiers for retention analytics."""
    day, visitor, person = date.today().isoformat(), _visitor(request), _person(request)
    referrer = _referrer(request)
    # Add to batch queue (will write to DB after 10 visits or 30 seconds)
    visit_batcher.add(day, body.surface, visitor, person, referrer)
    logger.info(f"visit queued surface={body.surface} batch_size={len(visit_batcher.batch)}")
    return {"ok": True}


@app.get("/v1/usage/stats")
@limiter.limit("60/minute")
def usage_stats(request: Request, days: int = 30, s: Session = Depends(get_db)):
    """Visitors and opens per day, landing page vs app. Aggregates only, no individual records."""
    days = max(1, min(days, 365))
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = s.query(db.Visit).filter(db.Visit.day >= since).all()
    per: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        d = per.setdefault(r.day, {"visitors": set(), "people": set(), "views": 0, "landing": 0, "app": 0})
        d["visitors"].add(r.visitor)
        if r.person:
            d["people"].add(r.person)
        d["views"] += 1
        d["landing" if r.surface == "landing" else "app"] += 1
    daily = [{"day": day, "visitors": len(d["visitors"]), "people": len(d["people"]), "views": d["views"], "landing_views": d["landing"], "app_opens": d["app"]}
             for day, d in sorted(per.items())]
    today = date.today().isoformat()
    by_person: Dict[str, set] = {}
    for r in rows:
        if r.person:
            by_person.setdefault(r.person, set()).add(r.day)
    people, people_today, returning = len(by_person), len({p for p, days_ in by_person.items() if today in days_}), sum(1 for days_ in by_person.values() if len(days_) > 1)
    return {"since": since, "days": days,
            "people": people, "people_today": people_today, "returning": returning,
            "visitors": len({r.visitor for r in rows}),
            "app_visitors": len({r.visitor for r in rows if r.surface == "app"}),
            "views": len(rows),
            "landing_views": sum(1 for r in rows if r.surface == "landing"),
            "app_opens": sum(1 for r in rows if r.surface == "app"),
            "today": next((d for d in daily if d["day"] == today), {"day": today, "visitors": 0, "views": 0, "landing_views": 0, "app_opens": 0}),
            "daily": daily,
            "note": "Visiteurs = hachage quotidien de l'IP et du navigateur, jamais conservé. Aucun cookie, aucun profil."}


OVERRIDE_FIELDS = {"ingredients_text": str, "fvn_pct": float, "protein_100g": float, "fiber_100g": float, "sugars_100g": float, "salt_100g": float, "fat_100g": float,
                   "saturated_fat_100g": float, "energy_kcal_100g": float}


def rescore(p: Dict[str, Any], strict: bool) -> Dict[str, Any]:
    """Same product, score recomputed in strict (Yuka-like) additive mode."""
    if not strict:
        return p
    q = {**p}
    q["score"] = score.quality(q, False, {**(p.get("scoreInputs") or {}), "strict": True})
    return q


def with_user_data(s: Session, uid: str, p: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
    """The product as this user completed it: their own values replace missing ones, the score is recomputed, and what came from them is listed."""
    row = s.query(db.ProductOverride).filter_by(user_id=uid, product_id=p["id"]).first()
    if not row:
        return rescore(p, strict)
    ov = json.loads(row.data)
    q = {**p, "nutriments": dict(p["nutriments"])}
    m = {"protein_100g": "protein100g", "fiber_100g": "fiber100g", "sugars_100g": "sugars100g", "salt_100g": "salt100g", "fat_100g": "fat100g", "saturated_fat_100g": "saturatedFat100g", "energy_kcal_100g": "energyKcal100g"}
    for k, nk in m.items():
        if ov.get(k) is not None:
            q["nutriments"][nk] = ov[k]
    if ov.get("ingredients_text"):
        q["ingredientsText"] = ov["ingredients_text"]
        q["dataQuality"] = {**q.get("dataQuality", {}), "ingredientsAvailable": True}
    q["score"] = score.quality(q, False, {**(p.get("scoreInputs") or {}), "fvn": ov.get("fvn_pct") if ov.get("fvn_pct") is not None else (p.get("scoreInputs") or {}).get("fvn"), "strict": strict})
    q["userData"] = sorted(ov)
    return q


class ContributeReq(BaseModel):
    ingredients_text: Optional[str] = Field(None, max_length=3000)
    fvn_pct: Optional[float] = Field(None, ge=0, le=100)
    protein_100g: Optional[float] = Field(None, ge=0, le=100)
    fiber_100g: Optional[float] = Field(None, ge=0, le=100)
    sugars_100g: Optional[float] = Field(None, ge=0, le=100)
    salt_100g: Optional[float] = Field(None, ge=0, le=100)
    fat_100g: Optional[float] = Field(None, ge=0, le=100)
    saturated_fat_100g: Optional[float] = Field(None, ge=0, le=100)
    energy_kcal_100g: Optional[float] = Field(None, ge=0, le=1000)


@app.post("/v1/products/{barcode}/contribute")
@limiter.limit("30/minute")
def contribute(request: Request, barcode: str, body: ContributeReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    """Complete a product's missing data yourself. Saved for you only; the score is recomputed from your values (shown as 'added by you')."""
    p = load_product(s, barcode)
    row = s.query(db.ProductOverride).filter_by(user_id=uid, product_id=p["id"]).first() or db.ProductOverride(user_id=uid, product_id=p["id"], data="{}")
    cur = json.loads(row.data)
    cur.update({k: v for k, v in body.dict().items() if v is not None and v != ""})
    row.data, row.updated_at = json.dumps(cur), db.now()
    s.add(row)
    s.commit()
    return {"product": with_user_data(s, uid, p)}


@app.delete("/v1/products/{barcode}/contribute")
def contribute_clear(barcode: str, uid: str = Depends(user), s: Session = Depends(get_db)):
    s.query(db.ProductOverride).filter_by(user_id=uid, product_id=barcode).delete()
    s.commit()
    return {"cleared": True}


class WebPricesReq(BaseModel):
    barcodes: List[str] = Field(..., min_length=1, max_length=8)


def _web_price_for(s: Session, barcode: str) -> Optional[Dict[str, Any]]:
    """An approximate web price (and the supermarkets it was found at) for a product with no observed price. None otherwise."""
    from . import webprice
    if not webprice.enabled():
        return None
    p = load_product(s, barcode)
    q = p.get("quantity")
    if not q or app.state.prices.latest(barcode, (q["amount"], q["unit"])):
        return None                       # an observed price exists, or the pack size is unknown: nothing to approximate
    return webprice.lookup(p)


@app.get("/v1/products/{barcode}/web-price")
@limiter.limit("20/minute")
def product_web_price(request: Request, barcode: str, uid: str = Depends(user), s: Session = Depends(get_db)):
    """One search for a product with no price: returns {price: {pack_cents, per100_cents, stores, chains, source_urls, approximate}} or {price: null}."""
    return {"price": _web_price_for(s, barcode)}


@app.post("/v1/web-prices")
@limiter.limit("10/minute")
def web_prices(request: Request, body: WebPricesReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    """The same for up to 8 alternatives at once (looked up in parallel). Returns {prices: {barcode: price-or-null}}."""
    from concurrent.futures import ThreadPoolExecutor
    from . import webprice
    codes = list(dict.fromkeys(body.barcodes))
    if not webprice.enabled():
        return {"prices": {c: None for c in codes}}
    products = {c: load_product(s, c) for c in codes}        # database reads stay on this thread
    q_of = lambda p: p.get("quantity")                      # noqa: E731
    todo = [c for c in codes if q_of(products[c]) and not app.state.prices.latest(c, (q_of(products[c])["amount"], q_of(products[c])["unit"]))]
    with ThreadPoolExecutor(max_workers=4) as ex:
        found = dict(zip(todo, ex.map(lambda c: webprice.lookup(products[c]), todo)))
    out = {}
    for c in codes:
        w = found.get(c)
        if w and w.get("per100_cents") is not None:     # the price-quality score at that approximate price, clearly marked approximate by the client
            vi_ = value_index.value_index(taxonomy.classify(products[c]).get("type"), (products[c].get("score") or {}).get("total"), w["per100_cents"])
            w = {**w, "value_score": vi_["value_score"] if vi_ else None}
        out[c] = w
    return {"prices": out}


@app.get("/v1/products/{barcode}")
def product(barcode: str, approximate: bool = False, strict: bool = True, uid: str = Depends(user), s: Session = Depends(get_db), lang: str = Depends(lang_of)):
    logger.info({"event": "product_lookup", "barcode": barcode, "user_id": uid})
    p = with_user_data(s, uid, load_product(s, barcode), strict)
    pr = prefs_of(s, uid)
    return {"product": p, "fit": engine.fit(p, pr.priorities, pr.allergens, None if pr.diet == "omnivore" else pr.diet, lang),
            "price_context": _price_context(s, uid, p, lang, approximate)}


def _record_price(s: Session, product_id: str, user_id: Optional[str], source: str, observed_on: Optional[str], pack_cents: Optional[int],
                  per100: Optional[float], qty: Optional[Dict[str, Any]], receipt_id: Optional[int] = None, confidence: str = "verified",
                  native: Optional[Dict[str, Any]] = None) -> None:
    """Store one observation for the product (deduplicated by product/source/date/user)."""
    if observed_on is None or (pack_cents is None and per100 is None):
        return
    q = s.query(db.ProductPrice).filter_by(product_id=product_id, source=source, observed_on=observed_on, user_id=user_id, receipt_id=receipt_id)
    if source != "receipt" and q.first():
        return
    s.add(db.ProductPrice(product_id=product_id, user_id=user_id, source=source, observed_on=observed_on, pack_cents=pack_cents, per100_cents=per100,
                          qty_amount=qty["amount"] if qty else None, qty_unit=qty["unit"] if qty else None, receipt_id=receipt_id, confidence=confidence,
                          currency=(native or {}).get("currency", market.currency()), price_native=(native or {}).get("price_native"), fx=(native or {}).get("fx"), stale=bool((native or {}).get("stale"))))


def _price_history(s: Session, uid: str, product_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    """The product's price observations (your receipts/entries and stored community observations), newest first. No shops."""
    rows = (s.query(db.ProductPrice).filter(db.ProductPrice.product_id == product_id)
            .filter((db.ProductPrice.user_id == uid) | (db.ProductPrice.user_id.is_(None)))
            .order_by(db.ProductPrice.observed_on.desc(), db.ProductPrice.id.desc()).limit(limit).all())
    return [{"id": r.id, "date": r.observed_on, "source": r.source, "pack_cents": r.pack_cents, "per100_cents": r.per100_cents, "confidence": r.confidence, "mine": r.user_id == uid,
             "currency": r.currency or market.currency(), "price_native": r.price_native, "fx": r.fx, "stale": bool(r.stale)} for r in rows]


def _own_price(s: Session, uid: str, product_id: str) -> Optional[Dict[str, Any]]:
    """Most recent price this user actually paid (from a confirmed receipt)."""
    pp = (s.query(db.ProductPrice).filter(db.ProductPrice.user_id == uid, db.ProductPrice.product_id == product_id, db.ProductPrice.source.in_(["receipt", "manual"]),
                                          db.ProductPrice.pack_cents.isnot(None)).order_by(db.ProductPrice.observed_on.desc(), db.ProductPrice.id.desc()).first())
    if pp:
        return {"unit_price_cents": pp.pack_cents, "date": pp.observed_on, "retailer": None}
    row = (s.query(db.PriceObservation).filter_by(user_id=uid, product_id=product_id)
           .order_by(db.PriceObservation.observed_on.desc(), db.PriceObservation.id.desc()).first())
    return None if not row else {"unit_price_cents": row.unit_price_cents, "date": row.observed_on, "retailer": row.retailer}


def _price_context(s: Session, uid: str, p: Dict[str, Any], lang: str = "fr", approximate: bool = False) -> Dict[str, Any]:
    own = _own_price(s, uid, p["id"])
    q = (p["quantity"]["amount"], p["quantity"]["unit"]) if p.get("quantity") else None
    comm = app.state.prices.latest(p["barcode"], q)
    base = (value.per100(own["unit_price_cents"], q) if (own and q) else None) or (comm["per100_cents"] if comm else None)
    if base is None and approximate:
        e0 = estimate.estimate_per100(p, [])
        base = e0[0] if (e0 and q) else None
    est = None
    if approximate and not own and not comm:
        e = estimate.estimate_per100(p, [])
        if e:
            est = {"per100_cents": e[0], "basis": e[1], "chains": estimate.chain_prices(e[0], q[0] if q else None)}
    real_base = (value.per100(own["unit_price_cents"], q) if (own and q) else None) or (comm["per100_cents"] if comm else None)    # observed prices only, never an estimate
    pq_score = value_index.value_index(taxonomy.classify(p).get("type"), (p.get("score") or {}).get("total"), real_base)
    hist = _price_history(s, uid, p["id"])
    vals = sorted(h["per100_cents"] for h in hist if h["per100_cents"] is not None and value.fresh(h["date"]))
    summary = {"n": len(hist), "median_per100_cents": vals[len(vals) // 2] if vals else None, "latest": hist[0] if hist else None}
    return {"history": hist, "summary": summary, "estimate": est, "your_last": own and {**own, "per100_cents": value.per100(own["unit_price_cents"], q) if q else None},
            "community": comm, "indicators": engine.indicators(p, base), "pack_size": p.get("quantity"), "value": pq_score,
            "note": tr(lang, "pc_note")}


def _month() -> str:
    from datetime import date
    return date.today().strftime("%Y-%m")


@app.get("/v1/insights")
@limiter.limit("10/minute")
def insights(request: Request, uid: str = Depends(user), s: Session = Depends(get_db), lang: str = Depends(lang_of)):
    """Grocery intelligence: where the money goes and verified-comparable ways to pay less."""
    rows = s.query(db.ReceiptItem, db.Receipt).join(db.Receipt).filter(db.Receipt.user_id == uid, db.ReceiptItem.is_discount == False).all()  # noqa: E712
    month = _month()
    receipts_all = s.query(db.Receipt).filter_by(user_id=uid).all()
    month_total = sum(r.total_cents or 0 for r in receipts_all if (r.purchase_date or "").startswith(month))
    month_n = sum(1 for r in receipts_all if (r.purchase_date or "").startswith(month))
    spend: Dict[str, Dict[str, Any]] = {}
    cat_spend: Dict[str, int] = {}
    for it, r in rows:
        k = it.matched_product_id or "raw:" + it.raw_description.lower()
        e = spend.setdefault(k, {"key": k, "name": it.raw_description, "product_id": it.matched_product_id, "spend_cents": 0, "times": 0, "last": None})
        e["spend_cents"] += it.line_total_cents or 0
        e["times"] += 1
        if not e["last"] or (r.purchase_date or "") >= (e["last"]["date"] or ""):
            e["last"] = {"date": r.purchase_date, "retailer": r.retailer, "unit_price_cents": it.unit_price_cents}
        cat = tr(lang, "other_cat")
        if it.matched_product_id:
            row = s.get(db.Product, it.matched_product_id)
            if row and row.category:
                cat = row.category.replace("en:", "").replace("-", " ")
        cat_spend[cat] = cat_spend.get(cat, 0) + (it.line_total_cents or 0)
    total_items = sum(cat_spend.values()) or 1
    top = sorted(spend.values(), key=lambda e: -e["spend_cents"])
    pr = prefs_of(s, uid)
    diet = None if pr.diet == "omnivore" else pr.diet
    opps, skipped = [], []
    for e in [x for x in top if x["product_id"]][:4]:
        orig = load_product(s, e["product_id"])
        q = orig.get("quantity")
        if not q:
            skipped.append({"name": orig["name"], "reason": tr(lang, "skip_size")})
            continue
        qty = (q["amount"], q["unit"])
        prio = pr.priorities or (["overall"] if orig["nutriScore"] else [])
        prio = [p for p in prio if p in engine.PRIORITIES]
        if not prio:
            skipped.append({"name": orig["name"], "reason": tr(lang, "skip_prio")})
            continue
        res = engine.choose(orig, _peers(s, orig, "similar", prio, pr.allergens), prio, pr.allergens, diet, "similar", 6, lang=lang)
        o100 = value.per100(e["last"]["unit_price_cents"], qty)
        # DB access stays on this thread (sessions are not thread-safe); only the network calls fan out.
        prep = []
        for a in res["alternatives"]:
            alt = a["product"]
            aq = alt.get("quantity")
            own = _own_price(s, uid, alt["id"]) if aq else None
            prep.append((alt, aq, own, aq is not None and not (own and value.fresh(own["date"]))))
        with ThreadPoolExecutor(max_workers=6) as ex:
            comms = _ctx_map(ex, lambda t: app.state.prices.latest(t[0]["barcode"], (t[1]["amount"], t[1]["unit"]), value.FRESH_DAYS) if t[3] else None, prep)
        pts = [value.price_point(alt, own, comm) if aq else None for (alt, aq, own, _), comm in zip(prep, comms)]
        best = None
        for a, pt in zip(res["alternatives"], pts):
            if not pt or a["product"]["quantity"]["unit"] != q["unit"] or pt["per100_cents"] >= o100 * 0.95:
                continue
            sav = (o100 - pt["per100_cents"]) * qty[0] / 100
            if not best or sav > best["saving_per_purchase_cents"]:
                alt = a["product"]
                def pe(prod, p100):
                    prot = prod["nutriments"].get("protein100g")
                    return None if prot is None or p100 <= 0 else round(prot / (p100 / 100), 1)
                best = {"saving_per_purchase_cents": round(sav), "alternative": {"id": alt["id"], "name": alt["name"], "brand": alt["brand"], "imageUrl": alt["imageUrl"], "quantityText": alt["quantityText"]},
                        "alt_price": {"per100_cents": round(pt["per100_cents"], 1), "source": pt["source"], "date": pt["date"], "where": pt["where"]},
                        "protein_g_per_euro": {"yours": pe(orig, o100), "alternative": pe(alt, pt["per100_cents"])},
                        "improvements": a["improvements"], "tradeoffs": a["tradeoffs"], "similarity": a["similarity"]}
        if best:
            opps.append({"product": {"id": orig["id"], "name": orig["name"], "brand": orig["brand"], "imageUrl": orig["imageUrl"]}, "times_bought": e["times"],
                         "your_price": {"pack_cents": e["last"]["unit_price_cents"], "per100_cents": round(o100, 1), "date": e["last"]["date"], "retailer": e["last"]["retailer"]},
                         **best, "caveats": [tr(lang, "cav_per100"),
                                             tr(lang, "cav_community") if best["alt_price"]["source"] == "open_prices" else tr(lang, "cav_yours"),
                                             tr(lang, "cav_cheaper")]})
    opps.sort(key=lambda o: -o["saving_per_purchase_cents"])
    return {"month": month, "month_spend_cents": month_total, "month_receipts": month_n,
            "top_products": [{**{k: v for k, v in e.items() if k != "key"}, "share": round(e["spend_cents"] / total_items, 3)} for e in top[:5]],
            "categories": sorted([{"category": c, "spend_cents": v, "share": round(v / total_items, 3)} for c, v in cat_spend.items()], key=lambda x: -x["spend_cents"])[:5],
            "opportunities": opps, "not_assessed": skipped,
            "total_potential_saving_per_purchase_cents": sum(o["saving_per_purchase_cents"] for o in opps),
            "limits": [tr(lang, "lim1"), tr(lang, "lim2"), tr(lang, "lim3")]}


class BudgetIn(BaseModel):
    period: str = Field("weekly", pattern="^(weekly|monthly|per_trip)$")
    amount_cents: int = Field(gt=0, lt=10_000_000)
    style: str = Field("balanced", pattern="^(stay|balanced|nutrition)$")
    savings_goal_cents: Optional[int] = Field(None, ge=0, lt=10_000_000)
    categories: Optional[Dict[str, int]] = None  # optional per-group budgets in cents


class ChooseIn(BaseModel):
    original_id: str
    alt_id: str
    expected_saving_cents: int = Field(ge=0, lt=1_000_000)
    original_per100_cents: Optional[float] = None


def _receipt_rows(s: Session, uid: str) -> List[Dict[str, Any]]:
    return [{"id": r.id, "date": r.purchase_date, "total_cents": r.total_cents} for r in s.query(db.Receipt).filter_by(user_id=uid)]


def _category_spend(s: Session, uid: str, start, end) -> Dict[str, int]:
    out: Dict[str, int] = {}
    q = s.query(db.ReceiptItem, db.Receipt).join(db.Receipt).filter(db.Receipt.user_id == uid, db.ReceiptItem.is_discount == False)  # noqa: E712
    for it, r in q:
        d = bud._d(r.purchase_date)
        if not d or not (start <= d <= end) or not it.matched_product_id:
            continue
        row = s.get(db.Product, it.matched_product_id)
        cat = (row.category or "").replace("en:", "").replace("-", " ") if row else ""
        if cat:
            out[cat] = out.get(cat, 0) + (it.line_total_cents or 0)
    return out


def _budget_state(s: Session, uid: str, today=None) -> Optional[Dict[str, Any]]:
    from datetime import date as _d
    today = today or _d.today()
    cfg = s.get(db.BudgetConfig, uid)
    if not cfg or not cfg.amount_cents:
        return None
    st = bud.status(cfg.period, cfg.amount_cents, _receipt_rows(s, uid), today)
    press = bud.pressure(st)
    changes = []
    if cfg.period != "per_trip":
        a, b = bud.window(cfg.period, today), bud.window(cfg.period, today, 1)
        changes = bud.category_changes(_category_spend(s, uid, *a), _category_spend(s, uid, *b))
    cat_budgets = json.loads(cfg.categories) if cfg.categories else {}
    groups: Dict[str, int] = {}
    if cat_budgets and cfg.period != "per_trip":
        a_, b_ = bud.window(cfg.period, today)
        q = s.query(db.ReceiptItem, db.Receipt).join(db.Receipt).filter(db.Receipt.user_id == uid, db.ReceiptItem.is_discount == False)  # noqa: E712
        for it, r in q:
            d_ = bud._d(r.purchase_date)
            if d_ and a_ <= d_ <= b_:
                row = s.get(db.Product, it.matched_product_id) if it.matched_product_id else None
                g = bud.category_group(json.loads(row.data).get("categories", [])) if row else "other"
                groups[g] = groups.get(g, 0) + (it.line_total_cents or 0)
    cat_status = [{"group": g, "budget_cents": v, "spent_cents": groups.get(g, 0), "used_pct": round(groups.get(g, 0) / v * 100, 1)} for g, v in cat_budgets.items()]
    return {"config": {"period": cfg.period, "amount_cents": cfg.amount_cents, "style": cfg.style, "savings_goal_cents": cfg.savings_goal_cents, "categories": cat_budgets},
            "category_status": cat_status,
            "status": st, "pressure": press, "recommended_ranking": bud.recommended_ranking(cfg.style, press), "category_changes": changes}


def _savings_state(s: Session, uid: str, today=None) -> Dict[str, Any]:
    from datetime import date as _d
    today = today or _d.today()
    first = today.replace(day=1).isoformat()
    cfg = s.get(db.BudgetConfig, uid)
    ev = s.query(db.SavingsEvent).filter_by(user_id=uid).all()
    realized = sum(e.realized_cents or 0 for e in ev if e.status == "realized" and (e.realized_at or "") >= first)
    chosen = [e for e in ev if e.status == "chosen"]
    return {"goal_cents": cfg.savings_goal_cents if cfg else None, "realized_cents": realized, "chosen_cents": sum(e.expected_saving_cents for e in chosen),
            "chosen_count": len(chosen), "realized_count": sum(1 for e in ev if e.status == "realized"), "chosen": len(chosen),
            "acceptance_pct": round(100 * sum(1 for e in ev if e.status == "realized") / len(ev)) if ev else None}


@app.put("/v1/me/budget")
def put_budget(body: BudgetIn, uid: str = Depends(user), s: Session = Depends(get_db)):
    cfg = s.get(db.BudgetConfig, uid) or db.BudgetConfig(user_id=uid)
    cfg.period, cfg.amount_cents, cfg.style, cfg.savings_goal_cents = body.period, body.amount_cents, body.style, body.savings_goal_cents
    cfg.categories = json.dumps({k: v for k, v in (body.categories or {}).items() if v > 0 and k in [g for g, _ in bud.GROUPS] + ['other']})
    s.merge(cfg)
    s.commit()
    return {"ok": True}


@app.delete("/v1/me/budget")
def delete_budget(uid: str = Depends(user), s: Session = Depends(get_db)):
    s.execute(delete(db.BudgetConfig).where(db.BudgetConfig.user_id == uid))
    s.commit()
    return {"ok": True}


@app.get("/v1/budget")
def get_budget(uid: str = Depends(user), s: Session = Depends(get_db)):
    """Budget status (updates as soon as a receipt is confirmed) + savings goal progress (potential is added by /v1/insights)."""
    return {"budget": _budget_state(s, uid), "savings": _savings_state(s, uid)}


@app.get("/v1/budget/summary")
def budget_summary(uid: str = Depends(user), s: Session = Depends(get_db)):
    return _budget_state(s, uid)


@app.get("/v1/budget/forecast")
def budget_forecast(uid: str = Depends(user), s: Session = Depends(get_db)):
    st = _budget_state(s, uid)
    return {"forecast": st["status"]["forecast"] if st else None, "note": "Estimation à partir de vos tickets confirmés ; pas une certitude." if st else None}


@app.get("/v1/savings")
def savings_summary(uid: str = Depends(user), s: Session = Depends(get_db)):
    return _savings_state(s, uid)


@app.get("/v1/prices")
def prices_search(product: str, uid: str = Depends(user), s: Session = Depends(get_db)):
    return {"history": _price_history(s, uid, product, 50)}


@app.post("/v1/savings/choose")
def choose_saving(body: ChooseIn, uid: str = Depends(user), s: Session = Depends(get_db)):
    """'I will buy this instead.' Counts as chosen (estimated), never as realized until a confirmed receipt shows the purchase."""
    s.add(db.SavingsEvent(user_id=uid, original_id=body.original_id, alt_id=body.alt_id, expected_saving_cents=body.expected_saving_cents,
                          original_per100_cents=body.original_per100_cents, status="chosen"))
    s.commit()
    return {"ok": True, "savings": _savings_state(s, uid)}


def _realize_savings(s: Session, uid: str, product_id: str, paid_pack_cents: int, receipt_id: int, day: Optional[str]) -> None:
    ev = s.query(db.SavingsEvent).filter_by(user_id=uid, alt_id=product_id, status="chosen").order_by(db.SavingsEvent.id).first()
    row = s.get(db.Product, product_id)
    q = json.loads(row.data).get("quantity") if row else None
    if not ev or not q or ev.original_per100_cents is None:
        return  # cannot compute honestly -> stays 'chosen'
    paid100 = value.per100(paid_pack_cents, (q["amount"], q["unit"]))
    ev.realized_cents = round((ev.original_per100_cents - paid100) * q["amount"] / 100)
    ev.status, ev.receipt_id, ev.realized_at = "realized", receipt_id, day or ""


class ExplainIn(BaseModel):
    original_id: str
    alt_id: str


@app.post("/v1/explain")
@limiter.limit("20/minute")
def explain_comparison(request: Request, body: ExplainIn, uid: str = Depends(user), s: Session = Depends(get_db), lang: str = Depends(lang_of)):
    """Plain-language explanation of original vs alternative. Numbers are computed here; a model can only rephrase them."""
    o, a = load_product(s, body.original_id), load_product(s, body.alt_id)
    o100, ap, pts, _ = _price_map(s, uid, o, [a])
    facts = exp.make_facts(o, a, o100, ap.get(a["barcode"]))
    return exp.explain(facts, lang, app.state.llm)


class ManualPrice(BaseModel):
    price_cents: int = Field(gt=0, lt=100000)
    date: Optional[str] = None


@app.post("/v1/products/{barcode}/prices")
@limiter.limit("30/minute")
def add_price(request: Request, barcode: str, body: ManualPrice, uid: str = Depends(user), s: Session = Depends(get_db)):
    """Enter the pack price you saw or paid. Stored against the product, not a shop."""
    from datetime import date as _d
    p = load_product(s, barcode)
    q = p.get("quantity")
    day = body.date or _d.today().isoformat()
    _record_price(s, p["id"], uid, "manual", day, body.price_cents, value.per100(body.price_cents, (q["amount"], q["unit"])) if q else None, q)
    s.commit()
    return {"ok": True, "history": _price_history(s, uid, p["id"])}


@app.get("/v1/products/{barcode}/prices")
def price_history(barcode: str, uid: str = Depends(user), s: Session = Depends(get_db)):
    return {"history": _price_history(s, uid, barcode)}


@app.delete("/v1/prices/{pid}")
def delete_price(pid: int, uid: str = Depends(user), s: Session = Depends(get_db)):
    r = s.get(db.ProductPrice, pid)
    if not r or r.user_id != uid:
        raise HTTPException(404, "Not found")
    s.delete(r)
    s.commit()
    return {"deleted": pid}


@app.post("/v1/geocode")
@limiter.limit("20/minute")
def geocode(request: Request, body: GeoReq, uid: str = Depends(user)):
    """Postcode/town -> coordinates via the French public geo API. Only the postcode or town name leaves the device."""
    import httpx
    params = {"fields": "nom,centre,codesPostaux", "limit": 1}
    if body.postcode:
        params["codePostal"] = body.postcode.strip()
    elif body.query:
        params["nom"] = body.query.strip()
    else:
        raise HTTPException(422, "postcode or query required")
    try:
        r = httpx.get("https://geo.api.gouv.fr/communes", params=params, timeout=8).json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Geocoding service unavailable")
    if not r:
        raise HTTPException(404, "Place not found")
    lon, lat = r[0]["centre"]["coordinates"]
    return {"lat": lat, "lon": lon, "label": r[0]["nom"]}


class AddressReq(BaseModel):
    query: str = Field(min_length=3, max_length=200)


@app.post("/v1/address")
@limiter.limit("40/minute")
def address_search(request: Request, body: AddressReq):
    """Free-text address -> properly formatted French addresses with coordinates (api-adresse.data.gouv.fr)."""
    import httpx
    try:
        r = httpx.get("https://api-adresse.data.gouv.fr/search/", params={"q": body.query.strip(), "limit": 5, "autocomplete": 1}, timeout=6).json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Address service unavailable")
    out = []
    for f in r.get("features", []):
        p, lon_lat = f.get("properties", {}), f.get("geometry", {}).get("coordinates")
        if not lon_lat or not p.get("label"):
            continue
        out.append({"label": p["label"], "city": p.get("city") or "", "postcode": p.get("postcode"), "lat": lon_lat[1], "lon": lon_lat[0],
                    "exact": p.get("type") in ("housenumber", "street")})
    return out


class RetailersReq(Loc):
    chains: List[str] = []  # restrict to these chain ids (empty = all)


@app.post("/v1/products/{barcode}/retailers")
@limiter.limit("20/minute")
def retailers(request: Request, barcode: str, body: RetailersReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    """Where to buy: the chains that list the product (chain discovery), each with its nearest branches to the position (geographic discovery)."""
    body.chains = [c for c in body.chains if c in retail.NAME_OF]
    p = load_product(s, barcode)
    q = p.get("quantity")
    app.state.prices.prefetch([barcode])
    sightings = app.state.prices.chain_summary(barcode, (q["amount"], q["unit"]) if q else None)  # every chain seen in France under this EAN, with its average price
    listings = retail.discover(s, p, sightings)
    pack_by = {retail.ID_OF[r["chain"]]: r.get("pack_cents") for r in sightings if r.get("chain") in retail.ID_OF}
    rows = []
    far_chains = 0
    for ls in listings:
        if ls.listing_status not in ("listed", "unverified") or (body.chains and ls.chain_id not in body.chains):
            continue
        near = retail.nearest(s, ls.chain_id, body.lat, body.lon, max(1.0, min(body.radius_km, 50.0)), k=3, refresh=False, widen=False)  # the full store list is loaded: exact, only inside the radius
        if not near:
            far_chains += 1
            continue
        rows.append({"chain": retail.NAME_OF.get(ls.chain_id, ls.chain_id), "chain_id": ls.chain_id, "listing_status": ls.listing_status, "match_type": ls.match_type, "confidence": ls.match_confidence,
                     "source": ls.source, "note": ls.note, "price_per100_cents": ls.price_per100_cents, "pack_cents": pack_by.get(ls.chain_id), "last_checked": ls.last_checked.date().isoformat() if ls.last_checked else None, "source_url": ls.source_url,
                     "nearest_store": near[0] if near else None, "second_store": near[1] if len(near) > 1 else None, "stores": near})
    rows.sort(key=lambda r: (r["nearest_store"] is None, (r["nearest_store"] or {}).get("distance_m", 0)))
    return {"barcode": barcode, "product": p["name"], "size": q, "retailers": rows, "radius_km": body.radius_km,
            "other_chains": [{"chain": n, "chain_id": i} for n, i in retail.ID_OF.items() if i not in {r["chain_id"] for r in rows} and retail.in_market(i, market.current())],
            "far_chains": far_chains, "filtered_out": len([ls for ls in listings if body.chains and ls.chain_id not in body.chains and ls.listing_status in ("listed", "unverified")]),
            "note": "A chain listing does not guarantee that the nearest branch has the product in stock."}


class SubReq(BaseModel):
    alt_id: str
    verdict: str = Field(pattern="^(ok|not_comparable)$")


@app.post("/v1/products/{barcode}/substitutions")
@limiter.limit("60/minute")
def substitution_verdict(request: Request, barcode: str, body: SubReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    """The user's verdict on an alternative. 'not_comparable' hides it from this user's future results for that product."""
    o, a = load_product(s, barcode), load_product(s, body.alt_id)
    sub = taxonomy.substitution(o, a)
    row = s.query(db.ProductSubstitution).filter_by(user_id=uid, original_id=o["id"], alt_id=a["id"]).first() or db.ProductSubstitution(user_id=uid, original_id=o["id"], alt_id=a["id"])
    row.verdict, row.level = body.verdict, (sub or {}).get("level")
    s.add(row)
    s.commit()
    return {"original": o["id"], "alt": a["id"], "verdict": row.verdict}


class ListingReq(BaseModel):
    chain_id: str
    url: Optional[str] = Field(None, max_length=500)


@app.post("/v1/products/{barcode}/listings")
@limiter.limit("30/minute")
def confirm_listing(request: Request, barcode: str, body: ListingReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    """User correction: 'I found this product at <chain>'. Saved as evidence with its source."""
    if body.chain_id not in retail.NAME_OF:
        raise HTTPException(422, "Unknown chain")
    p = load_product(s, barcode)
    r = retail.confirm(s, p["id"], body.chain_id, body.url)
    return {"chain_id": r.chain_id, "listing_status": r.listing_status, "match_type": r.match_type}


@app.post("/v1/products/{barcode}/store-prices")
@limiter.limit("30/minute")
def store_prices(request: Request, barcode: str, body: Loc, uid: str = Depends(user), s: Session = Depends(get_db), lang: str = Depends(lang_of)):
    """Price per shop near a location (community observations + your own receipts), cheapest first."""
    p = load_product(s, barcode)
    q = p.get("quantity")
    stores = app.state.prices.stores(barcode, (q["amount"], q["unit"]) if q else None, body.lat, body.lon, body.radius_km)
    own = _own_price(s, uid, p["id"])
    if own and q and value.fresh(own["date"]):
        stores.append({"store": own["retailer"] or "?", "name": own["retailer"], "city": None, "per100_cents": round(value.per100(own["unit_price_cents"], (q["amount"], q["unit"])), 1),
                       "pack_cents": own["unit_price_cents"], "date": own["date"], "distance_km": None, "source": "your_receipt"})
        stores.sort(key=lambda x: x["per100_cents"])
    est = None
    if not stores:
        e = estimate.estimate_per100(p, [])
        if e:
            est = {"basis": e[1], "per100_cents": e[0], "chains": estimate.chain_prices(e[0], q["amount"] if q else None)}
    return {"stores": stores, "estimated": est, "pack_size": q, "radius_km": body.radius_km,
            "note": tr(lang, "stores_note")}


@app.get("/v1/search")
def search(q: str, uid: str = Depends(user)):
    try:
        return {"products": [normalize(r) for r in app.state.off.search_name(q) if r.get("product_name")]}
    except OFFError as e:
        raise HTTPException(503, str(e))


@app.post("/v1/scans")
@limiter.limit("30/minute")
def add_scan(request: Request, body: Dict[str, str], uid: str = Depends(user), s: Session = Depends(get_db)):
    logger.info({"event": "scan_added", "barcode": body.get("barcode"), "user_id": uid})
    p = load_product(s, body["barcode"])
    if not is_account(s, uid):  # a signed-in account stores nothing here: its scan total lives in Supabase
        s.add(db.Scan(user_id=uid, product_id=p["id"]))
        s.commit()
    return {"ok": True, "product_id": p["id"]}


@app.get("/v1/scans")
def scans(uid: str = Depends(user), s: Session = Depends(get_db)):
    if is_account(s, uid):
        return {"scans": []}
    rows = s.query(db.Scan).filter_by(user_id=uid).order_by(db.Scan.id.desc()).limit(50).all()
    return {"scans": [{"id": r.id, "created_at": r.created_at.isoformat(), "product": json.loads(s.get(db.Product, r.product_id).data)} for r in rows]}


@app.get("/v1/me/preferences")
def get_prefs(uid: str = Depends(user), s: Session = Depends(get_db)):
    return prefs_of(s, uid)


@app.put("/v1/me/preferences")
def put_prefs(body: Prefs, uid: str = Depends(user), s: Session = Depends(get_db)):
    if is_account(s, uid):
        return body
    r = s.get(db.Preference, uid) or db.Preference(user_id=uid)
    r.diet, r.priorities, r.allergens = body.diet, json.dumps(body.priorities), json.dumps(body.allergens)
    s.merge(r)
    s.commit()
    return body


class MeIdentity(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    platform: Optional[str] = None  # web | ios | android | native


def _identity(row: Optional[db.User]) -> Dict[str, Any]:
    if row is None:
        return {"name": None, "city": None, "postcode": None, "platform": None, "first_seen": None, "last_seen": None}
    return {"name": row.name, "city": row.city, "postcode": row.postcode, "platform": row.platform,
            "first_seen": row.created_at.isoformat() if row.created_at else None,
            "last_seen": row.last_seen_at.isoformat() if row.last_seen_at else None}


@app.get("/v1/me/profile")
def get_identity(uid: str = Depends(user), s: Session = Depends(get_db)):
    """What is stored about this person: a first name and a city. No account, no e-mail, no password."""
    return _identity(s.get(db.User, uid))


@app.put("/v1/me/profile")
def put_identity(body: MeIdentity, uid: str = Depends(user), s: Session = Depends(get_db)):
    """Save the first name and city typed in the profile, so the owner can see who uses Mieux and the profile
    survives a cleared browser. Everything else (scans, receipts, prices) stays on the device."""
    if is_account(s, uid):
        return _identity(None)
    row = s.get(db.User, uid) or db.User(id=uid)
    row.name = (body.name or "").strip()[:80] or None
    row.city = (body.city or "").strip()[:80] or None
    row.postcode = (body.postcode or "").strip()[:12] or None
    row.platform = (body.platform or "").strip()[:16] or None
    row.last_seen_at = db.now()
    s.merge(row)
    s.commit()
    return _identity(row)


@app.get("/v1/people")
@limiter.limit("10/minute")
def people(request: Request, days: int = 30, limit: int = 100,
           x_admin_key: Optional[str] = Header(None), s: Session = Depends(get_db)):
    """Who is using Mieux: the names and cities people saved, newest activity first. Closed unless ADMIN_KEY is set
    and sent as X-Admin-Key, so this list is never public."""
    key = os.environ.get("ADMIN_KEY")
    if not key:
        raise HTTPException(404, "Not found")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, key):
        raise HTTPException(404, "Not found")
    days, limit = max(1, min(365, days)), max(1, min(500, limit))
    since = db.now() - timedelta(days=days)
    rows = [r for r in s.query(db.User).order_by(db.User.created_at.desc()).limit(5000).all() if (r.last_seen_at or r.created_at) and (r.last_seen_at or r.created_at) >= since]
    rows.sort(key=lambda r: r.last_seen_at or r.created_at, reverse=True)
    rows = rows[:limit]
    scans = dict(s.query(db.Scan.user_id, func.count(db.Scan.id)).group_by(db.Scan.user_id).all())
    return {"total_users": s.query(func.count(db.User.id)).scalar() or 0,
            "with_name": s.query(func.count(db.User.id)).filter(db.User.name.isnot(None)).scalar() or 0,
            "window_days": days,
            "people": [{**_identity(r), "id": r.id, "scans": scans.get(r.id, 0)} for r in rows],
            "note": "Sans compte : un identifiant d'appareil, le prénom et la ville saisis dans le profil."}


def _warm_stores(chains: List[str], lat: float, lon: float) -> None:
    """Background job: look up and store the nearest branches of these chains (OpenStreetMap, one request per second), so the next search is instant."""
    with app.state.sessions() as s2:
        for c in chains:
            try:
                retail.nearest(s2, c, lat, lon, 15, k=1)
            except Exception:
                continue


# Category tags too broad to say anything about the product: they are not worth a query.
_TOO_BROAD = {"en:foods", "en:plant-based-foods", "en:plant-based-foods-and-beverages", "en:groceries"}
# Raw nutrient keys that must be present for the priority to be compared at all (a missing value is never treated as zero).
_NEEDED = {"protein": ("proteins_100g",), "sugars": ("sugars_100g",), "fibre": ("fiber_100g",),
           "salt": ("salt_100g", "sodium_100g"), "saturated_fat": ("saturated-fat_100g",)}
# A priority read on the compact side index: column to order by, and whether lower is better.
_QUICK_ORDER = {"sugars": ("sugar", True), "salt": ("salt", True), "saturated_fat": ("sat", True),
                "protein": ("protein", False), "fibre": ("fibre", False), "overall": ("grade", True)}


_BRAND_CHAINS: Optional[Dict[str, List[str]]] = None


def _brand_chain_ids(brand: Optional[str]) -> List[str]:
    """Chains known to sell a brand, from scripts/build_brand_chains.py (evidence: its products seen in those chains' price data).
    A chain counts when it has at least 3 of the brand's products and at least 15 % of the best chain's count, so one stray sighting adds nothing."""
    global _BRAND_CHAINS
    if _BRAND_CHAINS is None:
        _BRAND_CHAINS = {}
        for path in (os.environ.get("BRAND_CHAINS"), "/data/brand_chains.json", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brand_chains.json")):
            if path and os.path.exists(path):
                try:
                    for r in json.load(open(path, encoding="utf-8")):
                        top = max([c["products"] for c in r["chains"]] or [0])
                        ids = [retail.ID_OF[c["chain"]] for c in r["chains"] if c["products"] >= max(3, 0.15 * top) and c["chain"] in retail.ID_OF]
                        if ids:
                            _BRAND_CHAINS[r["brand"]] = ids
                    break
                except (OSError, ValueError, KeyError):
                    continue
    key = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñ&' ]", " ", str(brand or "").split(",")[0].lower())).strip()
    return _BRAND_CHAINS.get(key, [])


_EXCLUDED_BRANDS = re.compile(r"marks\s*(&|and|et)\s*spencer|\bm\s*&\s*s\b|\bm&s\b", re.I)


def _raw_candidate(r: Dict[str, Any], priorities: List[str], allergens: List[str], orig: Dict[str, Any]) -> bool:
    """Cheap look at a raw Open Food Facts record, before the expensive normalisation and scoring.
    Drops what cannot become an alternative whatever its score: no name, not sold in France, no category, no value for the
    nutrient the person actually cares about, no ingredient list when an allergen has to be checked. A nutrient the scanned
    product itself does not have is not required: nothing could be compared on it anyway."""
    if not r.get("product_name"):
        return False
    if _EXCLUDED_BRANDS.search(str(r.get("brands") or "") + " " + str(r.get("product_name") or "")):
        return False       # chains that do not sell in France are never recommended
    countries = r.get("countries_tags")
    if countries and market.tag() not in countries:
        return False
    cats = r.get("categories_tags") or []
    if not cats:
        # A candidate without category tags is allowed through preliminary retrieval
        # when its name and other available attributes support classification.
        name = r.get("product_name") or ""
        cls = taxonomy.classify({"name": name, "categories": []})
        if not cls.get("type"):
            return False
    return True


def _raw_relevance(orig: Dict[str, Any], words: set):
    """Order raw candidates by how close they are to the scanned product, using only fields that are already in the record:
    same leaf category first, then same parent, then more shared categories, then shared name words. Ties keep the
    popular-first order of the database."""
    cats = orig["categories"]
    leaf = cats[-1] if cats else None
    parent = cats[-2] if len(cats) > 1 else None
    allc = set(cats)
    orig_name = engine._tok(orig["name"], orig["brand"])

    def key(r: Dict[str, Any]):
        rc = set(r.get("categories_tags") or [])
        name = engine._tok(r.get("product_name") or "", r.get("brands"))
        name_similarity = len(name & orig_name)
        category_match = 0 if leaf and leaf in rc else 1 if parent and parent in rc else 2
        # Product names are supporting evidence only. Competing products often
        # use a completely different name, so category/taxonomy evidence leads.
        return (category_match, -len(rc & allc), -name_similarity)
    return key


def _search_any(orig: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Products found by the names of the scanned product's type (OR search); empty when the type has no names or the data source cannot do it."""
    terms = taxonomy.search_terms(orig)
    fn = getattr(app.state.off, "search_any", None)
    if not terms or fn is None:
        return []
    try:
        return fn(terms)
    except Exception:
        return []


def _peers(s: Session, orig: Dict[str, Any], mode: str, priorities: Optional[List[str]] = None,
           allergens: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Candidate pool for the deep search, read from the whole local copy of Open Food Facts when it is there.

    EXHAUSTIVE RETRIEVAL: Removed arbitrary limits (500/1500/120). Now searches the entire relevant product type cohort
    without popularity bias. The engine's compatibility gate decides what is comparable, not retrieval limits.

    Every meaningful category level of the product is read, its own leaf category first then its parents. Products are
    retrieved via pagination to ensure all candidates are considered, not just the most popular ones.
    """
    base = [t for t in orig["categories"] if t not in _TOO_BROAD]
    if not base:
        # No usable category tags (common on thin Open Food Facts records): find candidates by what the product is called, through its type's names.
        found: Dict[str, Dict[str, Any]] = {}
        for r in _search_any(orig):
            if r.get("product_name") and _raw_candidate(r, priorities or [], allergens or [], orig):
                p = normalize(r)
                found.setdefault(p["barcode"], p)
        return list(found.values())
    tags = list(reversed(base))  # most specific first
    if mode != "similar":
        tags = tags[2:] or tags  # "any category": the leaf level is too narrow, start from the parent
    prio, alg = priorities or [], allergens or []
    local = getattr(getattr(app.state.off, "local", None), "available", lambda: False)()
    raws: List[Dict[str, Any]] = []
    # Whole categories, chosen in SQL: the best products on the chosen priority anywhere in the category, then the most
    # scanned ones, so a good product is not missed just because few people scan it. Falls back to the scanned-first
    # slices below when the compact index has not been built.
    # REMOVED ARBITRARY LIMITS: No per_tag=500, total=1500 limits. Search exhaustively.
    if local and getattr(app.state.off, "quick_available", lambda: False)():
        spec = _QUICK_ORDER.get(prio[0]) if prio else None
        required = []
        for p in prio:
            s = _QUICK_ORDER.get(p)
            if not s:
                continue
            if s[0] == "grade":
                if orig.get("nutriScore"):
                    required.append("grade")
            elif orig["nutriments"].get(engine.PRIORITIES[p][0]) is not None:
                required.append(s[0])
        # REMOVED LIMITS: No per_tag/total caps - retrieve full type cohort
        codes = app.state.off.quick_candidates(tags[:3], spec[0] if spec else None, spec[1] if spec else True,
                                               tuple(required), bool(alg))
        if codes:
            raws = app.state.off.quick_products(codes)
    if not raws:
        try:
            # REMOVED LIMITS: No per_tag/total caps - retrieve full type cohort
            raw = app.state.off.categories(tags[:4])
        except Exception:  # a missing or unreadable local copy must never break a scan
            raw = []
        # REMOVED LIMIT: No [:1500] slice - process all candidates
        raws = sorted([r for r in raw if _raw_candidate(r, prio, alg, orig)], key=_raw_relevance(orig, engine._tok(orig["name"], orig["brand"])))
    pool: Dict[str, Dict[str, Any]] = {}
    orig_name_words = engine._tok(orig["name"], orig["brand"])
    for r in raws:
        if not _raw_candidate(r, prio, alg, orig):
            continue
        # Retrieval is intentionally broader than ranking. Products with different names
        # and brands still reach taxonomy.substitution before being rejected or ranked.
        p = normalize(r)
        pool.setdefault(p["barcode"], p)
    # Candidates found by what the product IS (its type's names, OR-matched), whatever their brand calls them and however rarely they are scanned.
    for r in _search_any(orig):
        if r.get("product_name") and _raw_candidate(r, prio, alg, orig):
            p = normalize(r)
            pool.setdefault(p["barcode"], p)
    # Online searches only when there is no local copy: it covers the whole dataset, so a thin pool there means the
    # product really has few neighbours, and going online would just wait out the search rate limit (7 s per level).
    if len(pool) < 40 and not local:
        for tag in tags[:3]:
            try:
                for r in app.state.off.search_category(tag):
                    if r.get("product_name"):
                        p = normalize(r)
                        pool.setdefault(p["barcode"], p)
            except OFFError:
                continue
            if len(pool) >= 60:
                break
    if len(pool) < 40:
        # Name search is a last-resort supplement, never the primary way to
        # discover substitutes with different brand/product names.
        words = sorted(engine._tok(orig["name"], orig["brand"]), key=len, reverse=True)[:3]
        if words:
            try:
                for r in app.state.off.search_name(" ".join(words)):
                    if r.get("product_name"):
                        p = normalize(r)
                        pool.setdefault(p["barcode"], p)
            except (OFFError, AttributeError):
                pass
    return list(pool.values())


def _community(p: Dict[str, Any], loc: Optional[Loc] = None, max_age: int = 730, only: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Community price with EXPLICIT SCOPE SEPARATION.
    Returns price with scope field: 'store' (exact shop in radius), 'chain' (same retailer, any location), 'market' (France-wide), or 'estimate'.
    Scopes are preserved through the pipeline to prevent misleading local price claims.
    """
    q = p.get("quantity")
    if not q:
        return None

    # Scope 1: Exact store observation within radius
    if loc is not None:
        hit = getattr(app.state.prices, "store_price", lambda *_: None)(p["barcode"], (q["amount"], q["unit"]), loc.lat, loc.lon, loc.radius_km)
        if hit:
            return {**hit, "where": hit.get("store"), "per100_cents": hit["per100_cents"], "stale": False, "scope": "store"}

    # Scope 2: Chain-level observation (same retailer, any location)
    if only:
        chain_hit = app.state.prices.latest(p["barcode"], (q["amount"], q["unit"]), max_age, "FR", only)
        if chain_hit:
            return {**chain_hit, "where": None, "scope": "chain", "retailers": only}

    # Scope 3: Market-level observation (France-wide)
    pt = app.state.prices.latest(p["barcode"], (q["amount"], q["unit"]), max_age)
    return None if not pt else {**pt, "where": None, "scope": "market"}


def _fill_pack_prices(pool, prices, points):
    """A product with no price of its own takes the per-100 price of another pack size of the same product (same brand and name), marked as derived.
    Only observed prices are copied, never estimates."""
    by_key = {}
    for c in pool:
        pt = points.get(c["barcode"])
        if c["barcode"] in prices and pt and pt.get("source") != "estimate":
            by_key.setdefault(engine.variant_key(c), c["barcode"])
    for c in pool:
        if c["barcode"] in prices:
            continue
        src = by_key.get(engine.variant_key(c))
        if src:
            prices[c["barcode"]] = prices[src]
            points[c["barcode"]] = {**points[src], "derived": True}


def _with_confidence(pt):
    return {**pt, "confidence": value.price_confidence(pt)} if pt else None


_WARM = ThreadPoolExecutor(max_workers=2)


def _price_map(s: Session, uid: str, orig: Dict[str, Any], prods: List[Dict[str, Any]], loc: Optional[Loc] = None, approximate: bool = False, only: Optional[List[str]] = None):
    """Price per 100 g/ml for the original and a list of products: your own recent receipt/entry first, else a real community observation.
    DB access stays on this thread (sessions are not thread-safe); only the network calls fan out. Estimates only when approximate=True."""
    oq = orig.get("quantity")
    points: Dict[str, Any] = {}
    shops: Dict[str, List[Dict[str, Any]]] = {}
    prices: Dict[str, float] = {}
    orig_price = None
    if oq:
        own = _own_price(s, uid, orig["id"])
        comm = None if (own and value.fresh(own["date"])) else (_community(orig, loc, 730, only) or (_community(orig, loc, 730, None) if only else None))   # the scanned product's own price must not vanish just because it was not seen at the chosen chains: the product page shows the same unrestricted price
        pt = value.price_point(orig, own, comm)
        if pt:
            orig_price, points[orig["barcode"]] = pt["per100_cents"], pt
    prep = []
    for c in prods:
        cq = c.get("quantity")
        ok = cq is not None and (not oq or cq["unit"] == oq["unit"])
        ownc = _own_price(s, uid, c["id"]) if ok else None
        prep.append((c, cq, ownc, ok and not (ownc and value.fresh(ownc["date"]))))
    with ThreadPoolExecutor(max_workers=6) as ex:
        comms = _ctx_map(ex, lambda t: _community(t[0], loc, 730, only) if t[3] else None, prep)
    for (c, cq, ownc, _), comm in zip(prep, comms):
        pt = value.price_point(c, ownc, comm) if cq else None
        if pt and (not oq or cq["unit"] == oq["unit"]):
            prices[c["barcode"]] = pt["per100_cents"]
            points[c["barcode"]] = {k: pt[k] for k in ("source", "date", "where", "scope", "store", "distance_km") if k in pt}
            points[c["barcode"]].update({k: pt[k] for k in ("currency", "price_native", "fx", "stale", "pack_cents") if k in pt})
    if orig_price is not None:
        points[orig["barcode"]] = {k: points[orig["barcode"]][k] for k in ("source", "date", "where", "currency", "price_native", "fx", "stale", "pack_cents", "scope", "store", "distance_km") if k in points[orig["barcode"]]}
    # Too few observed prices for this kind of product (or none for the scanned one): search the web (Parallel, cached for good in webprice_cache.db) so the
    # price lists are never empty. Found prices carry source='web_search' + approximate=True; the clients show them with a "~".
    from . import webprice
    if webprice.enabled() and (len([b for b in prices if b != orig["barcode"]]) < 6 or (oq and orig_price is None)):
        todo = []
        if oq and orig_price is None:
            todo.append(orig)
        for c in prods:
            cq, sub = c.get("quantity"), c.get("substitution")
            if cq and c["barcode"] not in prices and c["barcode"] != orig["barcode"] and (not oq or cq["unit"] == oq["unit"]) and (sub is None or sub.get("level") in (1, 2)):
                todo.append(c)
            if len(todo) >= 10:
                break
        if todo:
            found = [webprice.cached_only(c) for c in todo]                 # instant: never wait on a search inside a request
            for c, w in zip(todo, found):
                if w is None:
                    _WARM.submit(webprice.lookup, c)                         # search in the background: next time it is stored
            for c, w in zip(todo, found):
                if not w or w.get("per100_cents") is None:
                    continue
                if c["barcode"] == orig["barcode"]:
                    orig_price = w["per100_cents"]
                else:
                    prices[c["barcode"]] = w["per100_cents"]
                points[c["barcode"]] = {"source": "web_search", "approximate": True, "date": w.get("date"), "where": ", ".join(w.get("stores") or []) or None, "stale": bool(w.get("stale")),
                                        "pack_cents": w.get("pack_cents")}
    if approximate:
        # Estimates only where nothing was observed, always tagged source='estimate' (never a verified price).
        observed = [v for k, v in prices.items() if k != orig["barcode"]]
        for c in [orig] + list(prods):
            q = c.get("quantity")
            if not q or (c["barcode"] in prices) or (c["barcode"] == orig["barcode"] and orig_price is not None) or (oq and q["unit"] != oq["unit"]):
                continue
            est = estimate.estimate_per100(c, observed)
            if est:
                if c["barcode"] == orig["barcode"]:
                    orig_price = est[0]
                else:
                    prices[c["barcode"]] = est[0]
                points[c["barcode"]] = {"source": "estimate", "date": None, "where": est[1]}
    # Keep community observations in the product price database so history accumulates (one row per product/date).
    for c in [orig] + list(prods):
        pt, q = points.get(c["barcode"]), c.get("quantity")
        p100 = orig_price if c["barcode"] == orig["barcode"] else prices.get(c["barcode"])
        if pt and pt.get("source") == "open_prices" and pt.get("date") and p100 is not None:
            _record_price(s, c["barcode"], None, "open_prices", pt["date"], round(p100 * q["amount"] / 100) if q else None, p100, q, native=pt)
    for bc, pt in points.items():  # a price observed at an exact shop is shown with that shop, never merged into a chain claim
        if (pt or {}).get("scope") == "store" and pt.get("store"):
            shops[bc] = [pt]
    s.commit()
    return orig_price, prices, points, shops


@app.post("/v1/products/{barcode}/alternatives")
@limiter.limit("20/minute")
def alternatives(request: Request, background: BackgroundTasks, barcode: str, body: AltReq, uid: str = Depends(user), s: Session = Depends(get_db), lang: str = Depends(lang_of)):
    bad = [p for p in body.priorities if p not in engine.PRIORITIES]
    if bad:
        raise HTTPException(422, f"Unknown priorities: {bad}")
    orig = with_user_data(s, uid, load_product(s, barcode), body.strict_additives)
    pr = prefs_of(s, uid)
    allergens = body.excluded_allergens if body.excluded_allergens is not None else pr.allergens
    diet = body.diet if body.diet is not None else (None if pr.diet == "omnivore" else pr.diet)
    peers = [rescore(c, body.strict_additives) for c in _peers(s, orig, body.category_mode, body.priorities, allergens)]
    # EXHAUSTIVE PRICE ENRICHMENT: Batch ALL candidates for price enrichment, not just first 160
    # Since retrieval is now exhaustive, we must enrich all candidates to avoid bias
    getattr(app.state.prices, "prefetch", lambda *_: None)([orig["barcode"]] + [c["barcode"] for c in peers])
    seen_fr = getattr(app.state.prices, "seen_in_france", lambda _b: False)
    peers = [({**c, "soldInFrance": True, "frEvidence": "open_prices"} if seen_fr(c["barcode"]) else c) for c in peers]
    body.chains = [c for c in body.chains if c in retail.NAME_OF]  # ids of chains that no longer exist (saved on the device) are ignored
    sel_names = [retail.NAME_OF[c] for c in body.chains]
    chain_of = getattr(app.state.prices, "chain_summary", None)
    if chain_of:
        for c in peers:  # chains known to list each candidate (from Open Prices, France)
            q_ = c.get("quantity")
            c["chains"] = [retail.ID_OF[r["chain"]] for r in chain_of(c["barcode"], (q_["amount"], q_["unit"]) if q_ else None) if r["chain"] in retail.ID_OF]
    # Popularity of each candidate: how often it is scanned (Open Food Facts) and whether chains are known to sell it. The money and quality
    # lists use it to keep obscure products from topping a ranking (see engine.is_popular).
    local_ = getattr(app.state.off, "local", None)
    if local_ is not None and hasattr(local_, "_q"):
        codes_ = [c["barcode"] for c in peers]
        scans_: Dict[str, int] = {}
        for i_ in range(0, len(codes_), 500):
            chunk_ = codes_[i_:i_ + 500]
            for code_, n_ in (local_._q(f"select code, scans from off_products where code in ({','.join('?' * len(chunk_))})", tuple(chunk_)) or []):
                scans_[code_] = n_ or 0
        peers = [{**c, "popularity": {"scans": scans_.get(c["barcode"], 0), "chains": len(c.get("chains") or [])}} for c in peers]
    if chain_of and body.chains:  # the person picked chains: drop what is known to be sold only elsewhere
        # Unknown is not a reason to exclude: Open Prices covers a minority of products, and discarding every product it has not
        # recorded would hide most good substitutes behind a dataset gap. This scopes the search; it is not an availability claim.
        want = set(body.chains)
        if any(c.get("chains") for c in peers):  # price service unreachable: no chain is known at all, keep the pool
            peers = [c for c in peers if not c.get("chains") or (set(c["chains"]) & want)]
    if body.nearby_only and body.location and chain_of:
        # "only what I can buy near me": a product stays if one of its chains (among the user's chains, if any) has a branch within the radius. Exact distances from the full store list.
        loc0 = body.location
        close = {cid for cid in retail.NAME_OF if retail.in_market(cid, market.current()) and retail._near(s, cid, loc0.lat, loc0.lon, loc0.radius_km)}
        allowed = close & set(body.chains) if body.chains else close
        peers = [c for c in peers if set(c.get("chains") or []) & allowed]
        res_filter = {"radius_km": loc0.radius_km, "chains_near": sorted(retail.NAME_OF[c] for c in allowed)}
    else:
        res_filter = None
    if body.same_size and (orig.get("quantity") or {}).get("amount"):
        oq_ = orig["quantity"]
        peers = [c for c in peers if (c.get("quantity") or {}).get("unit") == oq_["unit"] and 0.5 <= c["quantity"]["amount"] / oq_["amount"] <= 2.0]
    if body.category_mode == "similar":
        # hard substitution filter first (type / form / use), then the user's own "not comparable" verdicts; similarity and quality only rank what survives
        rejected = {r.alt_id for r in s.query(db.ProductSubstitution).filter_by(user_id=uid, original_id=orig["id"], verdict="not_comparable").all()}
        # learning from everyone: a pair that two different people flagged "not comparable" is hidden for all
        rejected |= {a for (a,) in s.query(db.ProductSubstitution.alt_id).filter_by(original_id=orig["id"], verdict="not_comparable").group_by(db.ProductSubstitution.alt_id).having(func.count(func.distinct(db.ProductSubstitution.user_id)) >= 2).all()}
        kept = []
        for c in peers:
            sub = taxonomy.substitution(orig, c)
            if sub is None or sub["level"] > body.substitution_max or c["id"] in rejected:
                continue
            kept.append({**c, "substitution": sub})
        peers = kept
    need_prices = bool({"budget", "value"} & set(body.priorities))
    note = None
    # The price comparison is always part of the answer. Pool = the engine's picks + the best-matching comparable products,
    # priced together (cached, threaded). Prices are never invented.
    pool_src = engine.prefilter(orig, peers, allergens, diet, body.category_mode, priorities=body.priorities)
    if need_prices:
        peers = pool_src
        orig_price, prices, points, shops = _price_map(s, uid, orig, peers, body.location, body.approximate, sel_names)
        res = engine.choose(orig, peers, body.priorities, allergens, diet, body.category_mode, body.limit, prices, orig_price, lang)
        pool = peers
    else:
        res = engine.choose(orig, peers, body.priorities, allergens, diet, body.category_mode, body.limit, None, None, lang)
        pool = list({c["barcode"]: c for c in [a["product"] for a in res["alternatives"]] + pool_src}.values())
        orig_price, prices, points, shops = _price_map(s, uid, orig, pool, body.location, body.approximate, sel_names)
        for a in res["alternatives"]:
            a["price_per_100_cents"] = prices.get(a["product"]["barcode"])
            a["value"] = engine.value_card(orig, a["product"], orig_price, a["price_per_100_cents"])
    _fill_pack_prices(pool, prices, points)
    for a in res["alternatives"]:
        a["indicators"] = engine.indicators(a["product"], prices.get(a["product"]["barcode"]))
    est_codes = frozenset(k for k, v in points.items() if (v or {}).get("source") == "estimate" and k != orig["barcode"])
    orig_est = (points.get(orig["barcode"]) or {}).get("source") == "estimate"
    res["rankings"] = engine.build_rankings(orig, pool, prices, orig_price, body.priorities, body.category_mode, lang, res["alternatives"], est_codes, orig_est, points=points)
    for key in ("budget", "value", "quality", "closest"):
        for r in res["rankings"].get(key, []):
            if not r.get("price_source"):
                r["price_source"] = _with_confidence(points.get(r["product"]["barcode"]))
            r["stores"] = shops.get(r["product"]["barcode"], [])

    # What Mieux can actually claim about each shown product: an exact-barcode observation at a shop near you, a chain-level listing,
    # a market listing, or nothing. These stay separate questions; a nearby branch is never turned into evidence of stock.
    def _availability(pr_: Dict[str, Any]):
        q_ = pr_.get("quantity")
        hit = None
        if body.location and q_ and hasattr(app.state.prices, "store_price"):
            hit = app.state.prices.store_price(pr_["barcode"], (q_["amount"], q_["unit"]), body.location.lat, body.location.lon, body.location.radius_km)
        if hit:
            return {"state": "observed_at_store", "store": hit.get("store"), "date": hit.get("date"), "distance_km": hit.get("distance_km")}, hit
        chain_ = _chains.own_brand_chain(pr_.get("brand")) or _chains.canon(str(pr_.get("brand") or "").split(",")[0]) or next((retail.NAME_OF[i] for i in pr_.get("chains") or [] if i in retail.NAME_OF), None)
        if chain_:
            return {"state": "seen_at_chain", "chain": chain_}, None   # a store brand is sold by that chain; the card names the chain
            return {"state": "seen_at_chain"}, None   # a store brand is sold by that chain
        if pr_.get("soldInFrance"):
            return {"state": "market_listed"}, None
        return {"state": "unknown"}, None
    for a_ in res.get("alternatives", []):
        a_["availability"], a_["store_price"] = _availability(a_["product"])
    orig_type_ = taxonomy.classify(res.get("original") or {}).get("type") if res.get("original") else None
    for key_ in ("budget", "value", "quality", "closest"):
        seen_, kept_ = set(), []
        for r_ in res["rankings"].get(key_, []):
            vk_ = engine.variant_key(r_["product"])
            if vk_ in seen_:
                continue    # the same product under another barcode or pack size is listed once
            seen_.add(vk_); kept_.append(r_)
            if r_.get("value_score") is None:      # the second headline score on every card whose price is known
                vi_ = value_index.value_index(orig_type_, (r_["product"].get("score") or {}).get("total"), r_.get("price_per_100_cents"))
                r_["value_score"] = vi_["value_score"] if vi_ else None
            own_ = _chains.own_brand_chain(r_["product"].get("brand")) or _chains.canon(str(r_["product"].get("brand") or "")) or _chains.canon(str(r_["product"].get("name") or ""))
            cid_ = retail.ID_OF.get(own_) if own_ else None
            if cid_ and cid_ not in (r_["product"].get("chains") or []):
                r_["product"]["chains"] = [cid_] + list(r_["product"].get("chains") or [])   # a store brand always shows its chain logo
            if not r_["product"].get("chains"):
                r_["product"]["chains"] = _brand_chain_ids(r_["product"].get("brand"))     # no sighting of this exact product: the brand's usual chains
            r_["availability"], r_["store_price"] = _availability(r_["product"])
        res["rankings"][key_] = kept_
    if "diagnostics" in res:
        res["diagnostics"]["eligible_cheapest"] = len(res["rankings"].get("budget", []))
        res["diagnostics"]["eligible_quality"] = len(res["rankings"].get("quality", []))
        res["diagnostics"]["eligible_best_value"] = len(res["rankings"].get("value", []))
    if body.location:
        # A product counts for a chain if it was seen at that chain anywhere in France; what matters here is the closest branch of that chain to the user's reference point.
        loc_, sel = body.location, set(body.chains)
        lists = [res["alternatives"]] + [res["rankings"].get(k_, []) for k_ in ("budget", "value", "quality", "closest")]
        prods = {x["product"]["barcode"]: x["product"] for lst in lists for x in lst}
        from collections import Counter
        cnt = Counter(c for pr_ in prods.values() for c in (pr_.get("chains") or []) if not sel or c in sel)
        wanted = [c for c, _ in cnt.most_common(10)]
        best = {}
        for i, c in enumerate(wanted):  # branches already stored come back instantly; at most two missing chains are fetched now, the rest in the background
            hit = retail.nearest(s, c, loc_.lat, loc_.lon, loc_.radius_km, k=1, widen=False,
                                 refresh=(i < 2 and retail._near(s, c, loc_.lat, loc_.lon, loc_.radius_km) == []))
            best[c] = hit[0] if hit else None
        missing = [c for c in wanted if best.get(c) is None]
        if missing:
            background.add_task(_warm_stores, missing, loc_.lat, loc_.lon)
        def near_of(pr_):
            opts = [(best[c], c) for c in (pr_.get("chains") or []) if best.get(c) and (not sel or c in sel)]
            if not opts:
                return None
            bst, c = min(opts, key=lambda o: o[0]["distance_m"])
            return {"store": retail.NAME_OF[c], "chain_id": c, "name": bst["name"], "distance_km": round(bst["distance_m"] / 1000, 1), "lat": bst["lat"], "lon": bst["lon"]}
        nmap = {bc: near_of(pr_) for bc, pr_ in prods.items()}
        for lst in lists:
            for x in lst:
                x["nearby"] = nmap.get(x["product"]["barcode"])
        # Only the substitute list may be reordered by local evidence. Cheapest, Best value and Best quality keep their strict
        # ordering: moving a pricier product above a cheaper one would make the label untrue.
        res["rankings"]["closest"].sort(key=lambda x: (x.get("availability", {}).get("state") != "observed_at_store", x["nearby"] is None))
        res["location_used"] = True
    oq2 = orig.get("quantity")
    res["original_size"] = oq2
    res["nearby_filter"] = res_filter
    res["same_size_applied"] = bool(body.same_size and (oq2 or {}).get("amount"))
    for lst in [res["alternatives"]] + [res["rankings"].get(k_, []) for k_ in ("budget", "value", "quality", "closest")]:
        for x in lst:  # every price is shown with its pack size, so unit prices of different formats are never mistaken for the same thing
            q3 = x["product"].get("quantity")
            p100 = x.get("price_per_100_cents") if x.get("price_per_100_cents") is not None else prices.get(x["product"]["barcode"])
            x["size"] = q3
            x["pack_cents"] = round(p100 * q3["amount"] / 100) if (p100 is not None and q3) else None
            x["size_ratio"] = round(q3["amount"] / oq2["amount"], 2) if (q3 and oq2 and q3.get("unit") == oq2.get("unit") and oq2.get("amount")) else None
    res["original_taxonomy"] = taxonomy.classify(orig)
    res["original_indicators"] = engine.indicators(orig, orig_price)
    res["original_sold_in_france"] = orig.get("soldInFrance")
    if engine.is_liquid(orig):  # liquids: say 100 ml and litre, not 100 g and kilo
        liq = lambda t_: t_.replace("pour 100 g", "pour 100 ml").replace("per 100 g", "per 100 ml").replace("le kilo", "le litre").replace("EUR/kg", "EUR/L").replace("/kg", "/L")
        for a_ in res["alternatives"]:
            a_["improvements"] = [liq(x) for x in a_["improvements"]]
            a_["tradeoffs"] = [liq(x) for x in a_["tradeoffs"]]
        for k_ in ("budget", "value"):
            for r_ in res["rankings"][k_]:
                r_["why"] = liq(r_["why"]); r_["tradeoffs"] = [liq(x) for x in r_["tradeoffs"]]
    bs = _budget_state(s, uid)
    if bs:
        oq_ = orig.get("quantity")
        pack = round(orig_price * oq_["amount"] / 100) if (orig_price is not None and oq_) else None
        res["budget"] = {"pressure": bs["pressure"], "recommended_ranking": bs["recommended_ranking"], "remaining_cents": bs["status"]["remaining_cents"],
                         "label": bs["status"]["label"], "pack_share_of_remaining_pct": round(pack / bs["status"]["remaining_cents"] * 100) if (pack and bs["status"]["remaining_cents"] > 0) else None}
    for r_ in res["rankings"]["budget"] + res["rankings"]["value"]:
        r_["estimated"] = (points.get(r_["product"]["barcode"]) or {}).get("source") == "estimate"
    for a_ in res["alternatives"]:
        a_["estimated"] = (points.get(a_["product"]["barcode"]) or {}).get("source") == "estimate"
    res["original_estimated"] = (points.get(orig["barcode"]) or {}).get("source") == "estimate"
    if body.price_constraint in ("cheaper", "same_or_cheaper") and orig_price is not None:
        # keep only alternatives with a known price that is lower (or not higher) per 100 g; unknown price never passes
        ok = (lambda p: p is not None and (p < orig_price if body.price_constraint == "cheaper" else p <= orig_price))
        res["alternatives"] = [a for a in res["alternatives"] if ok(prices.get(a["product"]["barcode"]))]
        if not res["alternatives"]:
            res["no_recommendation_reason"] = tr(lang, "no_alt")
    elif body.price_constraint != "any" and orig_price is None:
        res["price_constraint_ignored"] = True
    if orig_price is not None:
        res["paris_estimate"] = estimate.chain_prices(orig_price, (orig.get("quantity") or {}).get("amount"))
    for a in res["alternatives"]:
        a["price_source"] = _with_confidence(points.get(a["product"]["barcode"]))
        a["stores"] = shops.get(a["product"]["barcode"], [])
    oq = orig.get("quantity")
    res["original_price"] = None if orig_price is None else {"per100_cents": round(orig_price, 1), "pack_cents": round(orig_price * oq["amount"] / 100) if oq else None, "source": points.get(orig["barcode"])}
    if orig_price is None:
        note = tr(lang, "price_note_none")
    res["original_stores"] = shops.get(orig["barcode"], [])
    res["original"] = {"id": orig["id"], "name": orig["name"], "novaGroup": orig.get("novaGroup"), "nutriScore": orig["nutriScore"], "score": orig.get("score")}
    res["price_note"] = note or tr(lang, "price_note")
    if not is_account(s, uid):
        s.add(db.AlternativeResult(user_id=uid, original_product_id=barcode, request=body.model_dump_json(), response=json.dumps(res)[:200000]))
    s.commit()
    return res


@app.post("/v1/comparisons")
@limiter.limit("20/minute")
def comparisons(request: Request, body: CmpReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    P = [load_product(s, b) for b in body.product_ids]
    if not is_account(s, uid):
        s.add(db.Comparison(user_id=uid, product_ids=json.dumps(body.product_ids)))
    s.commit()
    prices = {}
    for p in P:
        q = p.get("quantity")
        own = _own_price(s, uid, p["id"])
        hist = _price_history(s, uid, p["id"], 1)
        if own and q:
            prices[p["id"]] = {"per100_cents": round(value.per100(own["unit_price_cents"], (q["amount"], q["unit"])), 1), "pack_cents": own["unit_price_cents"], "source": "your_receipt", "date": own["date"]}
        elif hist and hist[0]["per100_cents"] is not None:
            prices[p["id"]] = {"per100_cents": hist[0]["per100_cents"], "pack_cents": hist[0]["pack_cents"], "source": hist[0]["source"], "date": hist[0]["date"]}
        else:
            e = estimate.estimate_per100(p, []) if body.approximate else None
            prices[p["id"]] = {"per100_cents": e[0], "pack_cents": round(e[0] * q["amount"] / 100) if q else None, "source": "estimate", "date": None} if e else None
    return {"products": [{"id": p["id"], "name": p["name"], "nutriScore": p["nutriScore"], "brand": p.get("brand"), "imageUrl": p.get("imageUrl"), "score": (p.get("score") or {}).get("total"), "price": prices[p["id"]]} for p in P], **engine.compare(P)}


def _known(s: Session, uid: str) -> List[Dict[str, Any]]:
    ids = {r.product_id for r in s.query(db.Scan).filter_by(user_id=uid).all()}
    return [json.loads(s.get(db.Product, i).data) for i in ids]


def _dupe(s: Session, uid: str, retailer, date, total) -> Optional[db.Receipt]:
    return s.query(db.Receipt).filter_by(user_id=uid, retailer=retailer, purchase_date=date, total_cents=total).first()


@app.post("/v1/receipts/preview")
@limiter.limit("10/minute")
def receipts_preview(request: Request, body: PreviewReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    r = receipts.parse([l.model_dump() for l in body.lines])
    known = _known(s, uid)
    for i in r["items"]:
        i["match_candidate"] = None if i["is_discount"] else receipts.match(i["raw"], known)
    # Unmatched lines: look the description up by name in Open Food Facts. Candidates only; the user must confirm each one.
    todo = [i for i in r["items"] if not i["is_discount"] and not i["match_candidate"]][:8]
    def lookup(i):
        try:
            return receipts.best_name_match(i["raw"], app.state.off.search_name(i["raw"]))
        except OFFError:
            return None
    with ThreadPoolExecutor(max_workers=4) as ex:
        found = _ctx_map(ex, lookup, todo)
    for i, raw_p in zip(todo, found):
        if raw_p:
            p = normalize(raw_p)
            if not s.get(db.Product, p["id"]):
                s.add(db.Product(id=p["id"], name=p["name"], brand=p["brand"], category=p["category"], data=json.dumps(p)))
            i["match_candidate"] = {"product_id": p["id"], "name": p["name"], "score": raw_p["_score"], "source": "search"}
    s.commit()
    for i in r["items"]:  # explicit status per line; nothing is 'confirmed' until the user confirms it
        i["match_status"] = "probable" if i["match_candidate"] else "unidentified"
    for i in r["items"]:  # explicit status per line; nothing counts as confirmed until the user confirms it
        i["match_status"] = "probable" if i["match_candidate"] else "unidentified"
    r["possible_duplicate"] = bool(r["total_cents"] and _dupe(s, uid, r["retailer"], r["purchase_date"], r["total_cents"]))
    r["status"] = "review"
    return r


@app.post("/v1/receipts/confirm")
@limiter.limit("10/minute")
def receipts_confirm(request: Request, body: ConfirmReq, uid: str = Depends(user), s: Session = Depends(get_db)):
    total = body.total_cents if body.total_cents is not None else sum(i.line_total_cents for i in body.items)
    if _dupe(s, uid, body.retailer, body.purchase_date, total) and not body.allow_duplicate:
        raise HTTPException(409, "Possible duplicate receipt")
    r = db.Receipt(user_id=uid, retailer=body.retailer, purchase_date=body.purchase_date, total_cents=total)
    for i in body.items:
        r.items.append(db.ReceiptItem(raw_description=i.raw_description, matched_product_id=i.matched_product_id, quantity=i.quantity,
                                      unit_price_cents=i.unit_price_cents, line_total_cents=i.line_total_cents, is_discount=i.is_discount,
                                      extraction_confidence=i.extraction_confidence, match_confidence=i.match_confidence,
                                      match_status="confirmed" if i.matched_product_id else "unidentified"))
    s.add(r)
    s.flush()
    for i in body.items:
        if i.matched_product_id and not i.is_discount:
            s.add(db.PriceObservation(user_id=uid, receipt_id=r.id, product_id=i.matched_product_id, retailer=body.retailer,
                                      observed_on=body.purchase_date, unit_price_cents=i.unit_price_cents))
            _realize_savings(s, uid, i.matched_product_id, i.unit_price_cents, r.id, body.purchase_date)
            row_ = s.get(db.Product, i.matched_product_id)
            q_ = (json.loads(row_.data).get("quantity") if row_ else None)
            _record_price(s, i.matched_product_id, uid, "receipt", body.purchase_date, i.unit_price_cents,
                          value.per100(i.unit_price_cents, (q_["amount"], q_["unit"])) if q_ else None, q_, receipt_id=r.id)
    s.commit()
    return {"id": r.id, "total_cents": total}


@app.get("/v1/receipts")
def list_receipts(uid: str = Depends(user), s: Session = Depends(get_db)):
    rows = s.query(db.Receipt).filter_by(user_id=uid).order_by(db.Receipt.purchase_date.desc()).all()
    return {"receipts": [{"id": r.id, "retailer": r.retailer, "purchase_date": r.purchase_date, "total_cents": r.total_cents, "lines": len(r.items)} for r in rows]}


@app.get("/v1/purchases")
def purchases(uid: str = Depends(user), s: Session = Depends(get_db), lang: str = Depends(lang_of)):
    rows = s.query(db.ReceiptItem, db.Receipt).join(db.Receipt).filter(db.Receipt.user_id == uid, db.ReceiptItem.is_discount == False).all()  # noqa: E712
    g: Dict[str, Dict[str, Any]] = {}
    for it, r in rows:
        k = it.matched_product_id or it.raw_description.lower()
        e = g.setdefault(k, {"key": k, "name": it.raw_description, "product_id": it.matched_product_id, "times": 0, "history": []})
        e["times"] += 1
        e["history"].append({"date": r.purchase_date, "retailer": r.retailer, "unit_price_cents": it.unit_price_cents})
    for e in g.values():
        e["history"].sort(key=lambda h: h["date"] or "", reverse=True)
        e["last_price_cents"] = e["history"][0]["unit_price_cents"]
    total = sum(r.total_cents or 0 for r in s.query(db.Receipt).filter_by(user_id=uid))
    return {"purchases": sorted(g.values(), key=lambda e: -e["times"]), "recorded_spending_cents": total,
            "note": tr(lang, "purch_note")}


@app.delete("/v1/receipts/{rid}")
@limiter.limit("30/minute")
def del_receipt(request: Request, rid: int, uid: str = Depends(user), s: Session = Depends(get_db)):
    r = s.get(db.Receipt, rid)
    if not r or r.user_id != uid:
        raise HTTPException(404, "Receipt not found")
    s.execute(delete(db.PriceObservation).where(db.PriceObservation.receipt_id == rid))
    s.execute(delete(db.ProductPrice).where(db.ProductPrice.receipt_id == rid))
    s.delete(r)
    s.commit()
    return {"deleted": rid}


@app.get("/v1/me/export")
def export(uid: str = Depends(user), s: Session = Depends(get_db)):
    return {"preferences": prefs_of(s, uid), "receipts": [{"id": r.id, "retailer": r.retailer, "date": r.purchase_date, "total_cents": r.total_cents,
            "items": [{"raw": i.raw_description, "matched": i.matched_product_id, "line_total_cents": i.line_total_cents} for i in r.items]}
            for r in s.query(db.Receipt).filter_by(user_id=uid)], "scans": [x.product_id for x in s.query(db.Scan).filter_by(user_id=uid)]}


@app.delete("/v1/me")
def erase(uid: str = Depends(user), s: Session = Depends(get_db)):
    for m in (db.SavingsEvent, db.BudgetConfig, db.PriceObservation, db.ProductPrice, db.Scan, db.Comparison, db.AlternativeResult, db.Preference):
        s.execute(delete(m).where(m.user_id == uid))
    for r in s.query(db.Receipt).filter_by(user_id=uid).all():
        s.delete(r)
    s.execute(delete(db.User).where(db.User.id == uid))
    s.commit()
    return {"deleted": True}


# ---- auth endpoints
@app.post("/v1/auth/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, s: Session = Depends(get_db)):
    """Login with email and password (placeholder for local auth).

    In a real implementation, you would hash passwords and verify them.
    For now, this creates/returns a user and generates a JWT token.
    """
    # Simple implementation: use email as user_id
    user_id = body.email
    user = s.get(db.User, user_id)
    if not user:
        user = db.User(id=user_id)
        s.add(user)
        s.commit()

    token = create_access_token({"sub": user_id})
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}


@app.post("/v1/auth/register")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest, s: Session = Depends(get_db)):
    """Register a new user (placeholder for local auth).

    In a real implementation, you would hash the password before storing.
    """
    user_id = body.email
    if s.get(db.User, user_id):
        raise HTTPException(400, "User already exists")

    user = db.User(id=user_id)
    s.add(user)
    s.commit()

    token = create_access_token({"sub": user_id})
    return {"access_token": token, "token_type": "bearer", "user_id": user_id}


# ---- health endpoints
@app.get("/health")
@limiter.limit("60/minute")
def health_check(request: Request):
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "0.2"}


@app.get("/health/ready")
@limiter.limit("60/minute")
def readiness_check(request: Request):
    """Readiness check - verifies database connectivity."""
    try:
        # Try to create a session
        s = app.state.sessions()
        s.execute("SELECT 1")
        s.close()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(503, f"Not ready: {str(e)}")


DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist"))  # the built web app (npm run build): one server, one address, any device


@app.get("/{path:path}", include_in_schema=False)
def web_app(path: str):
    """Serves the built web app and its files; unknown paths return index.html so client-side routes (/product/123) work on refresh. API and docs are matched before this."""
    if path.startswith(("v1/", "docs", "openapi", "redoc")):
        raise HTTPException(404)
    index = os.path.join(DIST, "index.html")
    if os.path.exists(index):
        f = os.path.realpath(os.path.join(DIST, path))
        if path and os.path.isfile(f) and f.startswith(os.path.realpath(DIST) + os.sep):
            return FileResponse(f)
        return FileResponse(index)
    p = os.path.join(os.path.dirname(WEB), path)  # no build yet: the old single-file page and its icons
    if path in ("manifest.json", "icon-180.png", "icon-512.png") and os.path.exists(p):
        return FileResponse(p)
    if path == "" and os.path.exists(WEB):
        return FileResponse(WEB)
    raise HTTPException(404)
