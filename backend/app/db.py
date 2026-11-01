import json
import os
from datetime import datetime
from typing import Iterator

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


def now():
    return datetime.utcnow()


class User(Base):  # anonymous session user; an auth provider can map onto this later
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    supabase_id = Column(String, unique=True, nullable=True)  # Optional: link to Supabase auth
    name = Column(String, nullable=True)  # first name, only to know who is using the app
    city = Column(String, nullable=True)
    postcode = Column(String, nullable=True)
    platform = Column(String, nullable=True)  # web | ios | android
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)


class Preference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    diet = Column(String, default="omnivore")
    priorities = Column(Text, default="[]")
    allergens = Column(Text, default="[]")  # allergens/restrictions treated as hard exclusions


class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)  # barcode
    name = Column(String)
    brand = Column(String)
    category = Column(String, index=True)
    data = Column(Text)  # normalized JSON
    fetched_at = Column(DateTime, default=now)


class ProductSnapshot(Base):  # versioned raw responses for auditing reformulations
    __tablename__ = "product_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id"), index=True)
    source_updated_at = Column(String)
    raw = Column(Text)
    created_at = Column(DateTime, default=now)


class Scan(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id = Column(String, ForeignKey("products.id"))
    favourite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)


class Comparison(Base):
    __tablename__ = "comparisons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_ids = Column(Text)
    created_at = Column(DateTime, default=now)


class AlternativeResult(Base):
    __tablename__ = "alternatives"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_product_id = Column(String)
    request = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=now)


class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    retailer = Column(String)
    purchase_date = Column(String)
    currency = Column(String, default="EUR")
    total_cents = Column(Integer)
    status = Column(String, default="confirmed")
    created_at = Column(DateTime, default=now)
    items = relationship("ReceiptItem", cascade="all, delete-orphan", backref="receipt")


class ReceiptItem(Base):
    __tablename__ = "receipt_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), index=True)
    raw_description = Column(String)
    matched_product_id = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    unit_price_cents = Column(Integer)
    line_total_cents = Column(Integer)
    is_discount = Column(Boolean, default=False)
    extraction_confidence = Column(Float)
    match_confidence = Column(Float, nullable=True)
    user_confirmed = Column(Boolean, default=True)
    match_status = Column(String, nullable=True)  # exact | probable | confirmed | unidentified


class PriceObservation(Base):  # confirmed prices *paid by the user*; not shop shelf prices
    __tablename__ = "price_observations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), index=True)
    product_id = Column(String, index=True)
    retailer = Column(String)
    observed_on = Column(String)
    unit_price_cents = Column(Integer)
    source = Column(String, default="user_receipt")


class Visit(Base):
    """One anonymous visit per person, per surface, per day. No cookie, no user id: only a daily-rotating hash of
    IP + browser is stored, so people can be counted without being followed from one day to the next."""
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    surface = Column(String, nullable=False)  # landing | app
    visitor = Column(String, index=True, nullable=False)  # daily hash, never a raw IP or user agent
    referrer = Column(String, nullable=True)  # direct | internal | external (coarse on purpose)
    created_at = Column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("day", "surface", "visitor", name="uq_visit_day_surface_visitor"),)


def _add_missing_columns(eng) -> None:
    """Tiny forward migration for tables created by an earlier version of this file (create_all never alters tables)."""
    from sqlalchemy import inspect, text
    insp = inspect(eng)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in have:
                with eng.begin() as cx:
                    cx.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col.type.compile(eng.dialect)}"))


def make_session_factory(url: str = None):
    url = url or os.environ.get("DATABASE_URL", "sqlite:///./foodiq.db")  # PostgreSQL: postgresql+psycopg://...
    kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if url.startswith("sqlite") and ":memory:" in url:
        from sqlalchemy.pool import StaticPool
        kw["poolclass"] = StaticPool
    eng = create_engine(url, **kw)
    Base.metadata.create_all(eng)
    _add_missing_columns(eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


class ProductPrice(Base):
    """One price observation for a PRODUCT (not for a shop). Sources: receipt, manual, open_prices, estimate.
    The shop is deliberately not part of the key and is never used to rank or compare prices."""
    __tablename__ = "product_prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, index=True)
    user_id = Column(String, index=True, nullable=True)  # null = community observation
    source = Column(String)
    observed_on = Column(String)
    pack_cents = Column(Integer, nullable=True)
    per100_cents = Column(Float, nullable=True)  # cents per 100 g/ml, when the pack size is known
    qty_amount = Column(Float, nullable=True)
    qty_unit = Column(String, nullable=True)
    confidence = Column(String, default="verified")  # verified | estimated
    receipt_id = Column(Integer, nullable=True, index=True)
    currency = Column(String, default="EUR")  # currency of the ORIGINAL observation
    price_native = Column(Float, nullable=True)  # pack price exactly as observed, in that currency
    fx = Column(Float, nullable=True)  # EUR per 1 unit of that currency at conversion time
    stale = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)


class BudgetConfig(Base):
    __tablename__ = "budget_config"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    period = Column(String, default="weekly")  # weekly | monthly | per_trip
    amount_cents = Column(Integer, default=0)
    style = Column(String, default="balanced")  # stay | balanced | nutrition
    savings_goal_cents = Column(Integer, nullable=True)  # per month
    categories = Column(Text, nullable=True)  # JSON {group: cents} optional category budgets
    updated_at = Column(DateTime, default=now)


class SavingsEvent(Base):
    """potential (found, not stored) -> chosen (user said 'I will buy this instead') -> realized (a confirmed receipt shows they did)."""
    __tablename__ = "savings_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_id = Column(String)
    alt_id = Column(String, index=True)
    original_per100_cents = Column(Float, nullable=True)  # what the user paid for the original, per 100 g/ml, when chosen
    expected_saving_cents = Column(Integer, default=0)  # per purchase
    status = Column(String, default="chosen")  # chosen | realized
    realized_cents = Column(Integer, nullable=True)
    receipt_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=now)
    realized_at = Column(String, nullable=True)


class RetailChain(Base):
    """A supermarket chain operating in France (static reference data, seeded at start)."""
    __tablename__ = "retail_chains"
    id = Column(String, primary_key=True)  # carrefour, monoprix, ...
    name = Column(String, nullable=False)
    website = Column(String)
    has_catalogue = Column(Boolean, default=False)  # an online catalogue exists
    catalogue_access = Column(String, default="none")  # none | blocked | api | feed  (how Mieux may read it)
    coverage = Column(String, default="national")  # national | regional | location_dependent


class Store(Base):
    """A physical branch. Filled from OpenStreetMap lookups and kept, so later searches near the same place are instant."""
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    chain_id = Column(String, ForeignKey("retail_chains.id"), index=True, nullable=False)
    store_name = Column(String)
    address = Column(String)
    latitude = Column(Float, index=True, nullable=False)
    longitude = Column(Float, index=True, nullable=False)
    source = Column(String, default="openstreetmap")
    source_id = Column(String, unique=True)  # osm type+id
    active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=now)


class ChainProductListing(Base):
    """One relationship per (product, chain): the chain is known to list the product. Never duplicated per branch.
    'not_found' is never evidence of absence; unknown is the default and is simply not stored."""
    __tablename__ = "chain_product_listings"
    id = Column(Integer, primary_key=True)
    product_id = Column(String, index=True, nullable=False)
    chain_id = Column(String, ForeignKey("retail_chains.id"), index=True, nullable=False)
    retailer_product_id = Column(String)
    match_type = Column(String, default="exact_ean")  # exact_ean | own_brand | user_confirmed | name_brand_size | fuzzy
    match_confidence = Column(Float, default=1.0)
    listing_status = Column(String, default="listed")  # listed | unverified | not_found | discontinued
    price_per100_cents = Column(Float)  # optional
    currency = Column(String, default="EUR")
    source = Column(String)  # open_prices | own_brand | user | retailer_catalogue
    source_url = Column(String)
    last_checked = Column(DateTime, default=now)
    note = Column(String)  # e.g. '3 relevés, 2 magasins'


class ProductSubstitution(Base):
    """User verdict on a proposed alternative. 'not_comparable' removes it from that user's future results; 'ok' confirms it."""
    __tablename__ = "product_substitutions"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    original_id = Column(String, index=True, nullable=False)
    alt_id = Column(String, nullable=False)
    verdict = Column(String, nullable=False)  # ok | not_comparable
    level = Column(Integer)  # level proposed by the engine
    created_at = Column(DateTime, default=now)


class ProductOverride(Base):
    """Data the user added for a product whose database record is missing it (ingredients, vegetable share, protein, fibre...). Stays in this user's data only."""
    __tablename__ = "product_overrides"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    product_id = Column(String, index=True, nullable=False)
    data = Column(Text, nullable=False)  # json of the fields below
    updated_at = Column(DateTime, default=now)
