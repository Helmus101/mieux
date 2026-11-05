"""Approximate prices when no observed price exists. Everything returned here is an ESTIMATE and is always labelled as such;
estimates are never used for verified-saving claims. The chain indices and category prices are rough assumptions, not data."""
from statistics import median

from . import market
from typing import Any, Dict, List, Optional, Tuple

# Paris supermarkets and a rough price level relative to a national supermarket average (1.00). Assumption, not a measurement.
PARIS_CHAINS: List[Tuple[str, float]] = [
    ("Lidl", 0.86), ("Aldi", 0.86), ("Leclerc", 0.90), ("Auchan", 0.97), ("Carrefour", 1.00), ("Intermarché", 1.00), ("Grand Frais", 1.00),
    ("Carrefour City", 1.08), ("Marché U / U Express", 1.08), ("Franprix", 1.10), ("Casino / Petit Casino", 1.10), ("Monoprix", 1.15), ("Naturalia / Biocoop", 1.25),
]

# Typical national shelf prices in EUR per kg (or per litre for liquids), keyed by a substring of the Open Food Facts category tag.
# Rough hypotheses used only as a last resort when fewer than 3 comparable products have an observed price.
CATEGORY_EUR_PER_KG: List[Tuple[str, float]] = [
    ("yogurts", 3.2), ("fromages-blancs", 2.8), ("breakfast-cereals", 6.0), ("cereal-bars", 12.0), ("milks", 1.1), ("plant-based-milks", 1.8), ("breads", 4.5),
    ("pastas", 2.2), ("rices", 2.8), ("chocolate-spreads", 9.0), ("sweet-spreads", 9.0), ("spreads", 8.0), ("biscuits", 7.0), ("cookies", 7.0), ("chocolates", 13.0),
    ("cheeses", 12.0), ("butters", 10.0), ("fruit-juices", 1.9), ("sodas", 1.3), ("waters", 0.4), ("soups", 2.6), ("sauces", 5.0), ("olive-oils", 9.0), ("vegetable-oils", 3.5),
    ("coffees", 14.0), ("teas", 35.0), ("jams", 5.5), ("honeys", 12.0), ("potato-chips", 10.0), ("crackers", 7.0), ("compotes", 3.2), ("hams", 14.0), ("sausages", 10.0),
    ("canned", 4.0), ("frozen", 5.0), ("cakes", 7.0), ("snacks", 9.0), ("desserts", 4.5),
]


# United States: national average retail prices in USD per kg (per litre for milk), from the US Bureau of Labor Statistics "Average Price Data",
# September 2026, converted from per-lb / per-gallon / per-dozen. Public-domain figures for staples only (series APU0000701111 flour, 701312 rice, 701322 pasta,
# 702111 bread, 703112 ground beef, 704111 bacon, 706111 whole chicken, FF1101 chicken breast, FD3101 pork chops, 708111 eggs, 709112 milk, 710212 cheddar,
# 711211 bananas, 711311 oranges, 711415 lemons, 712112 potatoes, 712311 tomatoes, 715211 sugar, 717311 coffee). A national average, not a store price.
CATEGORY_USD_PER_KG: List[Tuple[str, float]] = [
    ("ground-beef", 14.97), ("minced-beef", 14.97), ("bacons", 14.90), ("chicken-breasts", 9.27), ("pork-chops", 9.30), ("whole-chickens", 4.55),
    ("cheddar", 13.52), ("chicken-eggs", 3.34), ("-eggs", 3.34), ("whole-milks", 1.08), ("semi-skimmed-milks", 1.08), ("skimmed-milks", 1.08), ("cow-milks", 1.08),
    ("white-breads", 4.03), ("sliced-breads", 4.03), ("spaghetti", 3.03), ("pastas", 3.03), ("long-grain-rices", 2.46), ("white-rices", 2.46), ("rices", 2.46),
    ("wheat-flours", 1.20), ("white-sugars", 2.25), ("ground-coffees", 20.57), ("coffees", 20.57), ("bananas", 1.45), ("oranges", 3.80), ("lemons", 6.26),
    ("potatoes", 2.18), ("tomatoes", 4.39),
]


def category_price_per100(categories: List[str]) -> Optional[float]:
    """Cents per 100 g/ml from the market's category table, using the most specific matching category."""
    table = CATEGORY_USD_PER_KG if market.current() == "US" else CATEGORY_EUR_PER_KG
    for tag in reversed(categories):
        for key, per_kg in table:
            if key in tag:
                return per_kg * 10.0
    return None


def estimate_per100(product: Dict[str, Any], observed_peers: List[float]) -> Optional[Tuple[float, str]]:
    """(cents per 100 g/ml, basis) with basis 'peers' (median of >=3 observed comparable prices) or 'category' (static table)."""
    if len(observed_peers) >= 3:
        return round(median(observed_peers), 1), "peers"
    c = category_price_per100(product.get("categories", []))
    return (round(c, 1), "category") if c else None


def chain_prices(per100_cents: float, qty_amount: Optional[float]) -> List[Dict[str, Any]]:
    """Estimated price per Paris chain = estimate x chain index. Cheapest first."""
    if market.current() != "FR":
        return []
    out = []
    for name, idx in PARIS_CHAINS:
        p100 = per100_cents * idx
        out.append({"chain": name, "index": idx, "per100_cents": round(p100, 1), "pack_cents": None if not qty_amount else round(p100 * qty_amount / 100.0)})
    return sorted(out, key=lambda x: x["per100_cents"])
