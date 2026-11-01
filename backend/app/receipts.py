"""Deterministic receipt parsing (no LLM for prices or arithmetic). Money is integer cents."""
import re
import unicodedata
from typing import Any, Dict, List, Optional

STORES = ["carrefour", "monoprix", "leclerc", "auchan", "lidl", "aldi", "intermarch", "franprix", "casino", "picard", "super u",
          "u express", "hyper u", "biocoop", "naturalia", "grand frais", "cora", "match"]
SKIP = re.compile(r"\b(cb|carte|esp[eè]ces?|rendu|visa|mastercard|tva|monnaie|bancaire|ticket|sans contact|merci|caisse|siret|tel|fid[eé]lit[eé]|cumul|articles?|nb|net a payer|paiement|pourcentage|%)\b", re.I)
PRICE_END = re.compile(r"(-?\d{1,4}[.,]\d{2})\s*(?:€|eur|[A-Z]{1,2})?\s*$", re.I)
QTY = re.compile(r"(\d+)\s*[xX]\s*(\d+[.,]\d{2})\s*$")

# Retailer-specific parsing rules
RETAILER_RULES = {
    "carrefour": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "NET A PAYER"],
        "skip_keywords": ["CARTE BANCAIRE", "ESPECES", "REMISE", "CARTE", "CB"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "monoprix": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "A PAYER"],
        "skip_keywords": ["CB", "ESPECES", "FIDELITE", "REMISE"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "leclerc": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "NET A PAYER"],
        "skip_keywords": ["CARTE", "ESPECES", "REMISE", "CB"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "auchan": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "NET A PAYER"],
        "skip_keywords": ["CB", "ESPECES", "REMISE"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "lidl": {
        "date_pattern": r"(\d{2})\.(\d{2})\.(\d{4})",
        "total_keywords": ["TOTAL", "SUMME"],
        "skip_keywords": ["KARTE", "BAR", "RABATT"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "aldi": {
        "date_pattern": r"(\d{2})\.(\d{2})\.(\d{4})",
        "total_keywords": ["TOTAL", "SUMME"],
        "skip_keywords": ["KARTE", "BAR", "RABATT"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "intermarch": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "NET A PAYER"],
        "skip_keywords": ["CB", "ESPECES", "REMISE"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "franprix": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "A PAYER"],
        "skip_keywords": ["CB", "ESPECES", "REMISE"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
    "casino": {
        "date_pattern": r"(\d{2})/(\d{2})/(\d{4})",
        "total_keywords": ["TOTAL", "NET A PAYER"],
        "skip_keywords": ["CB", "ESPECES", "REMISE"],
        "item_pattern": r"^(.+?)\s+(\d+[.,]\d{2})\s*€?$",
    },
}


def cents(s: str) -> int:
    return int(round(float(s.replace(",", ".")) * 100))


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def detect_retailer(lines: List[str]) -> Optional[str]:
    """Detect retailer from receipt header."""
    header_text = " ".join(lines[:5]).lower()
    for retailer in RETAILER_RULES.keys():
        if retailer in header_text:
            return retailer
    return None


def parse(lines: List[Dict[str, Any]], retailer: str = None) -> Dict[str, Any]:
    """Parse receipt lines. If retailer is specified, use retailer-specific rules."""
    texts = [(l["text"].strip(), float(l.get("confidence", 0.9))) for l in sorted(lines, key=lambda l: l.get("position", 0)) if l["text"].strip()]
    
    # Detect retailer if not provided
    if not retailer:
        retailer = detect_retailer([t for t, _ in texts])
    
    # Get retailer-specific rules or use defaults
    rules = RETAILER_RULES.get(retailer.lower()) if retailer else None
    
    store, date, total, items = None, None, None, []
    
    # Extract store name
    for t, _ in texts[:8]:
        if retailer and retailer.lower() in fold(t):
            store = re.sub(r"[^\w' .-]", "", t).strip()
            break
        elif any(s in fold(t) for s in STORES):
            store = re.sub(r"[^\w' .-]", "", t).strip()
            break
    if not store:
        store = next((t[:30] for t, _ in texts if re.search(r"[A-Za-z]{4,}", t)), None)
    
    # Extract date with retailer-specific pattern
    # Receipts print dates as dd/mm/yyyy, dd.mm.yy, dd-mm-yyyy... so the generic pattern is used for every retailer.
    date_pattern = re.compile(r"(\d{2})[/.-](\d{2})[/.-](\d{4}|\d{2})\b")
    for t, _ in texts:
        m = date_pattern.search(t)
        if m:
            y = m.group(3) if len(m.group(3)) == 4 else "20" + m.group(3)
            date = f"{y}-{m.group(2)}-{m.group(1)}"
            break
    
    # Use the original SKIP regex for general parsing
    for t, conf in texts:
        m = PRICE_END.search(t)
        if not m:
            continue
        c = cents(m.group(1))
        body = t[:m.start()].strip()
        
        if re.search(r"sous[- ]?total", t, re.I):
            continue
        if re.search(r"total|a payer|à payer|montant", t, re.I):
            total = max(total or 0, c)
            continue
        # A negative amount is a discount line (loyalty, voucher, global discount): keep it so the lines add up to the printed total.
        if c < 0 and re.search(r"[A-Za-zÀ-ÿ]{2,}", body):
            items.append({"raw": body, "quantity": 1, "unit_price_cents": c, "line_total_cents": c, "is_discount": True, "extraction_confidence": round(min(conf, 0.7), 2)})
            continue
        if SKIP.search(t) or not re.search(r"[A-Za-zÀ-ÿ]{2,}", body):
            continue
        
        qty, unit = 1, None
        q = QTY.search(body)
        if q:
            qty, unit = int(q.group(1)), cents(q.group(2))
            body = QTY.sub("", body).strip()
        
        disc = c < 0 or bool(re.search(r"remise|r[eé]duc|promo", body, re.I))
        items.append({
            "raw": body or t,
            "quantity": qty,
            "unit_price_cents": unit if unit is not None else (round(c / qty) if qty else c),
            "line_total_cents": c,
            "is_discount": disc,
            "extraction_confidence": round(min(conf, 0.7 if disc else 0.95), 2)
        })
    
    s = sum(i["line_total_cents"] for i in items)
    warnings = []
    if total is None:
        warnings.append("No total detected.")
    elif total != s:
        warnings.append(f"Items sum ({s/100:.2f}) differs from total ({total/100:.2f}).")
    
    return {
        "retailer": store,
        "purchase_date": date,
        "total_cents": total,
        "items": items,
        "warnings": warnings,
        "detected_retailer": retailer
    }


def tokens(s: str) -> List[str]:
    s = re.sub(r"yaourt|yogourt|yog\b", "yaourt", fold(s))
    return [t for t in re.split(r"[^a-z0-9]+", s) if len(t) > 2]


def best_name_match(raw: str, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Best Open Food Facts search result for a receipt line, by token overlap. Returns the raw record plus '_score' (>= 0.6) or None."""
    T = set(tokens(raw))
    if not T:
        return None
    best = None
    for r in results:
        P = set(tokens((r.get("product_name") or "") + " " + (r.get("brands") or "")))
        hit = sum(1 for t in T if t in P or (len(t) >= 4 and any(x.startswith(t) for x in P)))
        sc = hit / len(T)
        if hit and (best is None or sc > best[0]):
            best = (sc, r)
    return None if not best or best[0] < 0.6 else {**best[1], "_score": round(best[0], 2)}


def match(raw: str, known: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Returns a *candidate* only; the user must confirm it. Never silently links."""
    T = tokens(raw)
    best = None
    for p in known:
        P = set(tokens((p["name"] or "") + " " + (p.get("brand") or "")))
        hit = sum(1 for t in T if t in P or (len(t) >= 4 and any(x.startswith(t) for x in P)))
        sc = hit / len(T) if T else 0
        if hit and (best is None or sc > best["score"]):
            best = {"product_id": p["id"], "name": p["name"], "score": round(sc, 2)}
    return best if best and best["score"] >= 0.5 else None
