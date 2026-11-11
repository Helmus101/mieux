"""Rough per-chain price levels applied to a price that WAS observed or found. There is no guess for a product without a price:
category and peer averages were removed on purpose. The chain indices are assumptions, not data."""
from . import market
from typing import Any, Dict, List, Optional, Tuple

# Paris supermarkets and a rough price level relative to a national supermarket average (1.00). Assumption, not a measurement.
PARIS_CHAINS: List[Tuple[str, float]] = [
    ("Lidl", 0.86), ("Aldi", 0.86), ("Leclerc", 0.90), ("Auchan", 0.97), ("Carrefour", 1.00), ("Intermarché", 1.00), ("Grand Frais", 1.00),
    ("Carrefour City", 1.08), ("Marché U / U Express", 1.08), ("Franprix", 1.10), ("Casino / Petit Casino", 1.10), ("Monoprix", 1.15), ("Naturalia / Biocoop", 1.25),
]

def chain_prices(per100_cents: float, qty_amount: Optional[float]) -> List[Dict[str, Any]]:
    """Estimated price per Paris chain = estimate x chain index. Cheapest first."""
    if market.current() != "FR":
        return []
    out = []
    for name, idx in PARIS_CHAINS:
        p100 = per100_cents * idx
        out.append({"chain": name, "index": idx, "per100_cents": round(p100, 1), "pack_cents": None if not qty_amount else round(p100 * qty_amount / 100.0)})
    return sorted(out, key=lambda x: x["per100_cents"])
