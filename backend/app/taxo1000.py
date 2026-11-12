"""Mieux 1000+ food taxonomy (app/mieux_taxonomy.json): assigns a product to one or more product_type nodes.

Matching is keyword-based and deliberately simple: a node matches when every content token of its French name (or one of
its examples) appears in the product's name / generic name. All fully-matching nodes are kept (a product can be several
types at once, e.g. "Steak haché de bœuf" is both "Bœuf haché" and "Steak haché de bœuf"); the most specific one - the
most matched tokens - is the primary type. This is a retrieval hint, not proof of interchangeability: the hard
substitution gate in taxonomy.py still decides what may be recommended.
"""
import json
import os
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mieux_taxonomy.json")
_STOP = {"de", "la", "le", "les", "des", "du", "d", "l", "en", "et", "a", "au", "aux", "un", "une", "the", "of", "and", "for", "with", "sur", "dans", "par", "pour"}
_MAX_TYPES = 8


def _norm(s: Optional[str]) -> str:
    s = (s or "").lower().replace("œ", "oe").replace("æ", "ae")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _tokens(s: Optional[str]) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _norm(s)) if t not in _STOP and len(t) > 1]


@lru_cache(maxsize=1)
def _load() -> Dict[str, Any]:
    data = json.load(open(_PATH, encoding="utf-8"))
    nodes = {n["id"]: n for n in data["nodes"]}
    # token -> [(node_id, alias_key)] ; alias_key = frozenset of the alias tokens that must all be present
    index: Dict[str, List[Tuple[str, frozenset]]] = {}
    types: Dict[str, Dict[str, Any]] = {}
    for n in data["nodes"]:
        if n.get("level") != 3:
            continue
        aliases = [n.get("name_fr") or ""]
        for part in re.split(r"[;|]", n.get("examples") or ""):
            if part.strip():
                aliases.append(part.strip())
        if n.get("name_en"):
            aliases.append(n["name_en"])
        seen = set()
        for alias in aliases:
            toks = frozenset(_tokens(alias))
            if not toks or toks in seen:
                continue
            seen.add(toks)
            for t in toks:
                index.setdefault(t, []).append((n["id"], toks))
        parent = nodes.get(n.get("parent_id") or "") or {}
        grand = nodes.get(parent.get("parent_id") or "") or {}
        types[n["id"]] = {"id": n["id"], "name": n.get("name_fr"), "parent": parent.get("id"), "category": parent.get("name_fr"),
                          "department": grand.get("name_fr"), "group": n.get("substitution_group"), "unit": n.get("comparison_unit")}
    return {"index": index, "types": types}


def classify(name: Optional[str], generic_name: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
    """Product type assignment for one product. Returns primary type id, all matching type ids, substitution groups,
    and the level-2 category / department ids. Empty lists when nothing matches confidently."""
    idx = _load()
    prod_tokens = frozenset(_tokens(" ".join(x for x in (name, generic_name) if x)))
    if not prod_tokens:
        return {"type": None, "types": [], "groups": [], "category": None, "department": None}
    candidates = set()
    for t in prod_tokens:
        candidates.update(idx["index"].get(t, ()))
    matched: Dict[str, int] = {}
    for nid, toks in candidates:
        if toks <= prod_tokens:
            matched[nid] = max(matched.get(nid, 0), len(toks))
    if not matched:
        return {"type": None, "types": [], "groups": [], "category": None, "department": None}
    ranked = sorted(matched.items(), key=lambda kv: (-kv[1], kv[0]))[:_MAX_TYPES]
    types = [idx["types"][nid] for nid, _ in ranked if nid in idx["types"]]
    primary = types[0] if types else None
    groups = list(dict.fromkeys(t["group"] for t in types if t.get("group")))
    return {"type": primary["id"] if primary else None, "types": [t["id"] for t in types], "groups": groups,
            "category": primary.get("parent") if primary else None, "department": primary.get("department") if primary else None,
            "primary": primary}


def node(node_id: str) -> Optional[Dict[str, Any]]:
    return _load()["types"].get(node_id)
