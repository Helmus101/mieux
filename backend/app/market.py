"""Which market (country) a request is for. The web app sends it as X-Country on every call; France is the default.
Each market has its own local Open Food Facts copy, so a French shopper never gets US alternatives and the other way round."""
import contextvars
import re
from typing import Any

MARKETS = {"FR": "france", "US": "united-states"}
_current: "contextvars.ContextVar[str]" = contextvars.ContextVar("market", default="FR")


def set_current(code: Any) -> str:
    c = str(code or "").strip().upper()
    c = c if c in MARKETS else "FR"
    _current.set(c)
    return c


def current() -> str:
    return _current.get()


def tag(code: str = "") -> str:
    """Open Food Facts country tag for a market code (default: this request's market), e.g. 'en:united-states'."""
    return "en:" + MARKETS.get(code or current(), "france")


CURRENCY = {"FR": "EUR", "US": "USD"}


def currency(code: str = "") -> str:
    return CURRENCY.get(code or current(), "EUR")


def localize_money(text: str) -> str:
    """Sentences are written with euros ('7,30 €', '7.30 EUR/kg', 'g/€'). For a US shopper they become dollars ('$7.30/kg', 'g/$'). Other markets are unchanged."""
    if current() != "US" or not text:
        return text
    text = re.sub(r"(\d[\d.,]*)\s?(?:€|EUR)", r"$\1", text)
    return text.replace("g/EUR", "g/$").replace("g/€", "g/$").replace("per euro", "per dollar").replace("par euro", "par dollar").replace("EUR", "USD").replace("€", "$")


class PerMarket:
    """Looks like one OFFClient but forwards every call to the client of the request's market."""
    def __init__(self, clients: dict):
        self._clients = clients

    def __getattr__(self, name: str):
        return getattr(self._clients.get(current()) or self._clients["FR"], name)
