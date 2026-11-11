"""Natural-language explanation of a comparison. All numbers come from the engine (facts). A language model may only rephrase them;
its output is rejected if it contains any number that is not in the facts, or a health claim. The deterministic template is the fallback."""
import os
import re

import httpx

from . import market
from typing import Any, Dict, List, Optional, Protocol, Set


class LLM(Protocol):
    def complete(self, system: str, user: str) -> Optional[str]: ...


def make_facts(orig: Dict[str, Any], alt: Dict[str, Any], orig100: Optional[float], alt100: Optional[float]) -> Dict[str, Any]:
    """Every number the explanation may mention. Differences are alt minus original, per 100 g/ml."""
    a, b = orig["nutriments"], alt["nutriments"]
    d = lambda f: None if a.get(f) is None or b.get(f) is None else round(b[f] - a[f], 1)  # noqa: E731
    f: Dict[str, Any] = {"original": orig["name"], "alternative": alt["name"], "protein_diff": d("protein100g"), "sugars_diff": d("sugars100g"), "fibre_diff": d("fiber100g"),
                         "salt_diff": d("salt100g"), "sat_fat_diff": d("saturatedFat100g"), "kcal_diff": None if d("energyKcal100g") is None else round(d("energyKcal100g")),
                         "nova_original": orig.get("novaGroup"), "nova_alternative": alt.get("novaGroup")}
    if orig100 and alt100:
        f.update({"price_per_kg_original": round(orig100 / 10, 2), "price_per_kg_alternative": round(alt100 / 10, 2), "price_diff_pct": round((alt100 - orig100) / orig100 * 100)})
    return f


T = {
    "fr": {"cheaper": "{alt} coûte {p} % moins cher au kilo que {orig} ({a} € contre {o} €).", "pricier": "{alt} coûte {p} % plus cher au kilo que {orig} ({a} € contre {o} €).",
           "more": "{n} g de {what} en plus pour 100 g", "less": "{n} g de {what} en moins pour 100 g", "join": " ; ", "but": " Côté nutrition : ", "end": ".", "nova": " Il est plus transformé (NOVA {a} → {b}).",
           "none": "Les données disponibles ne permettent pas de chiffrer la différence.", "what": {"protein": "protéines", "sugars": "sucres", "fibre": "fibres", "salt": "sel", "sat": "graisses saturées"}},
    "en": {"cheaper": "{alt} costs {p}% less per kg than {orig} ({a} EUR vs {o} EUR).", "pricier": "{alt} costs {p}% more per kg than {orig} ({a} EUR vs {o} EUR).",
           "more": "{n} g more {what} per 100 g", "less": "{n} g less {what} per 100 g", "join": "; ", "but": " Nutrition: ", "end": ".", "nova": " It is more processed (NOVA {a} -> {b}).",
           "none": "The available data does not allow quantifying the difference.", "what": {"protein": "protein", "sugars": "sugars", "fibre": "fibre", "salt": "salt", "sat": "saturated fat"}},
}


def template(f: Dict[str, Any], lang: str = "fr") -> str:
    t = T["fr" if lang == "fr" else "en"]
    fmt = lambda x: f"{x:g}".replace(".", ",") if lang == "fr" else f"{x:g}"  # noqa: E731
    parts: List[str] = []
    if f.get("price_diff_pct") is not None and f["price_diff_pct"] != 0:
        key = "cheaper" if f["price_diff_pct"] < 0 else "pricier"
        parts.append(t[key].format(alt=f["alternative"], orig=f["original"], p=abs(f["price_diff_pct"]), a=fmt(f["price_per_kg_alternative"]), o=fmt(f["price_per_kg_original"])))
    nut = []
    for k, w in (("protein_diff", "protein"), ("fibre_diff", "fibre"), ("sugars_diff", "sugars"), ("sat_fat_diff", "sat"), ("salt_diff", "salt")):
        v = f.get(k)
        if v is not None and abs(v) >= 0.1:
            nut.append(t["more" if v > 0 else "less"].format(n=fmt(abs(v)), what=t["what"][w]))
    text = "".join(parts)
    if nut:
        text += t["but"] + t["join"].join(nut) + t["end"]
    if f.get("nova_original") and f.get("nova_alternative") and f["nova_alternative"] > f["nova_original"]:
        text += t["nova"].format(a=f["nova_original"], b=f["nova_alternative"])
    return text.strip() or t["none"]


_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_BANNED = re.compile(r"(toxi|dangereu|cancer|guéri|soigne|poison|miracle|toxic|dangerous|cures?|harmful)", re.I)


def allowed_numbers(f: Dict[str, Any]) -> Set[str]:
    out = {"100", "1000", "1", "10"}
    for v in f.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            for x in (abs(v), v):
                for dec in (0, 1, 2):
                    s = f"{abs(x):.{dec}f}"
                    out.update({s, s.replace(".", ","), s.rstrip("0").rstrip(".") or "0", (s.rstrip("0").rstrip(".") or "0").replace(".", ",")})
    return out


def valid(text: str, f: Dict[str, Any]) -> bool:
    if not text or len(text) > 450 or _BANNED.search(text):
        return False
    names = f"{f.get('original', '')} {f.get('alternative', '')}"
    ok = allowed_numbers(f) | set(_NUM.findall(names))  # digits inside product names are fine
    return all(n in ok for n in _NUM.findall(text))


SYSTEM = {"fr": "Tu reformules une comparaison de deux produits alimentaires en 2 phrases maximum, en français. N'utilise QUE les nombres fournis dans les faits. N'ajoute aucune information, aucune affirmation de santé, aucun conseil médical.",
          "en": "You rephrase a comparison of two food products in at most 2 sentences. Use ONLY the numbers given in the facts. Add no information, no health claim, no medical advice."}


def explain(f: Dict[str, Any], lang: str, llm: Optional[LLM]) -> Dict[str, Any]:
    base = market.localize_money(template(f, lang))
    if llm is None:
        return {"text": base, "source": "template", "facts": f}
    out = llm.complete(SYSTEM["fr" if lang == "fr" else "en"], f"Faits : {f}\nPhrase de référence : {base}")
    if out and valid(out, f):
        return {"text": out, "source": "llm", "facts": f}
    return {"text": base, "source": "template", "facts": f, "llm_rejected": bool(out)}


def score_facts(p: Dict[str, Any]) -> Dict[str, Any]:
    """Every number a score explanation may mention, taken from the computed score (never invented)."""
    s = p.get("score") or {}
    f: Dict[str, Any] = {"original": p.get("name"), "total": s.get("total")}
    for part in s.get("parts") or []:
        key = part.get("key")
        if key:
            f[f"part_{key}"] = round(float(part.get("got") or 0))
    if s.get("caps"):
        f["caps"] = len(s["caps"])
    conf = (s.get("confidence") or {}).get("pct")
    if conf is not None:
        f["confidence_pct"] = conf
    if p.get("novaGroup"):
        f["nova"] = p["novaGroup"]
    return {k: v for k, v in f.items() if v is not None}


ST = {
    "fr": {"lead": "Note de qualité : {total}/100.", "parts": {"nutrition": "nutrition", "additives": "additifs", "ingredients": "ingrédients", "organic": "bio"},
           "part": " {label} {n}/100.", "caps": " La note est plafonnée par {n} point(s) faible(s).", "confidence": " Données complètes à {p} %."},
    "en": {"lead": "Quality score: {total}/100.", "parts": {"nutrition": "nutrition", "additives": "additives", "ingredients": "ingredients", "organic": "organic"},
           "part": " {label} {n}/100.", "caps": " The score is capped by {n} weakness(es).", "confidence": " Data {p}% complete."},
}


def score_template(f: Dict[str, Any], lang: str = "fr") -> str:
    t = ST["fr" if lang == "fr" else "en"]
    text = t["lead"].format(total=f.get("total"))
    for k, label in t["parts"].items():
        if f.get(f"part_{k}") is not None:
            text += t["part"].format(label=label, n=f[f"part_{k}"])
    if f.get("caps"):
        text += t["caps"].format(n=f["caps"])
    if f.get("confidence_pct") is not None:
        text += t["confidence"].format(p=f["confidence_pct"])
    return text.strip()


SCORE_SYSTEM = {"fr": "Tu expliques une note de qualité alimentaire en 2 phrases maximum, en français. N'utilise QUE les nombres fournis dans les faits. N'ajoute aucune information, aucune affirmation de santé, aucun conseil médical.",
                "en": "You explain a food quality score in at most 2 sentences. Use ONLY the numbers given in the facts. Add no information, no health claim, no medical advice."}


def score_explain(f: Dict[str, Any], lang: str, llm: Optional[LLM]) -> Dict[str, Any]:
    """The deterministic sentence is the fallback; a model may only rephrase the same facts."""
    base = market.localize_money(score_template(f, lang))
    if llm is None:
        return {"text": base, "source": "template", "facts": f}
    out = llm.complete(SCORE_SYSTEM["fr" if lang == "fr" else "en"], f"Faits : {f}\nPhrase de référence : {base}")
    if out and valid(out, f):
        return {"text": out, "source": "llm", "facts": f}
    return {"text": base, "source": "template", "facts": f, "llm_rejected": bool(out)}


class GeminiLLM:
    """Rephrases facts with Gemini. Any failure returns None so callers keep the deterministic template."""

    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, transport=None):
        self._transport = transport or _http_post

    def complete(self, system: str, user: str) -> Optional[str]:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            return None
        models = [m for m in (os.environ.get("GEMINI_MODEL"), "gemini-3.8-flash", "gemini-2.5-flash") if m]
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300, "thinkingConfig": {"thinkingBudget": 0}}}
        for model in dict.fromkeys(models):
            try:
                resp = self._transport(self.endpoint.format(model=model) + "?key=" + key, body, None, 15)
            except Exception:
                continue
            cands = (resp or {}).get("candidates") or []
            if not cands:
                continue
            text = "".join(part.get("text", "") for part in ((cands[0].get("content") or {}).get("parts") or []))
            if text.strip():
                return text.strip()
        return None


def _http_post(url: str, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: float = 25) -> Optional[Dict[str, Any]]:
    r = httpx.post(url, json=body, headers=headers, timeout=timeout)
    return r.json() if r.status_code == 200 else None
