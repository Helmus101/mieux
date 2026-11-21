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
_COLOURS = {"noir", "blanc", "vert", "rouge", "rose", "jaune", "bleu", "gris", "brun", "dore", "black", "white", "green", "red", "yellow", "blue"}


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


def classify(name: Optional[str], generic_name: Optional[str] = None, brand: Optional[str] = None, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """Placement of one product in the Mieux taxonomy: department > category > product type.

    The rule layer (taxorules: multilingual name rules plus the product's OFF category tags) decides first. It returns the deepest
    level it can justify: a specific product type (level 3), else a category (level 2), else a department (level 1). Only when no
    rule fires does the older alias matcher below try; if that finds nothing too the product is reported as level 0 (unclassified)
    rather than forced into a wrong box. Returns type id, all matching type ids, substitution groups, category and department ids."""
    from . import taxorules
    hit = taxorules.match(name, generic_name, categories)
    idx = _load()
    if hit:
        t = idx["types"].get(hit["type"]) if hit["type"] else None
        node_ = taxorules.load()["nodes"]
        group = (t or {}).get("group") or (node_[hit["category"]].get("substitution_group") or ("SG_" + hit["category"][2:]) if hit.get("category") else None)
        types = [hit["type"]] if hit["type"] else []
        groups = [group] if group else []
        # Other types the alias matcher also finds stay in `types` / `groups` as retrieval hints (the primary stays first).
        extra = _classify_alias(name, generic_name)
        for tid in extra.get("types") or []:
            if tid not in types:
                types.append(tid)
        for g in extra.get("groups") or []:
            if g not in groups:
                groups.append(g)
        if hit["level"] < 3:
            # Alternatives compare products of one specific type: a category-only or department-only placement carries no substitution group.
            types, groups = [], []
        return {"type": hit["type"], "types": types[:_MAX_TYPES], "groups": groups, "category": hit["category"],
                "department": hit["department"], "level": hit["level"], "source": hit["source"], "primary": t}
    out = _classify_alias(name, generic_name)
    out.setdefault("level", 3 if out.get("type") else 0)
    out.setdefault("source", "alias" if out.get("type") else None)
    return out


def _classify_alias(name: Optional[str], generic_name: Optional[str] = None) -> Dict[str, Any]:
    """The original keyword-alias matcher: every content token of a type's name (or example) must appear in the product name."""
    idx = _load()
    prod_tokens = frozenset(_tokens(" ".join(x for x in (name, generic_name) if x)))
    if not prod_tokens:
        return {"type": None, "types": [], "groups": [], "category": None, "department": None}
    candidates = set()
    for t in prod_tokens:
        candidates.update(idx["index"].get(t, ()))
    matched: Dict[str, int] = {}
    for nid, toks in candidates:
        # A single leftover word ("noir", "vert", "blanc", "orange") is a colour or flavour, not a product type: it only counts when it IS the product name.
        if toks <= prod_tokens and (len(toks) >= 2 or (prod_tokens == toks and not (toks & _COLOURS))):
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
