"""The alternatives database (alt_index.db, built by scripts/build_alt_index.py).

One row per product that may be recommended today: it has a brand, at least one supermarket chain and a real observed price.
Everything else in Open Food Facts / Open Prices stays in the scan-lookup databases (off_local.db, op_local.db). Because the
three requirements are guaranteed here, a request only has to pick the product's category, apply the shopper's filters and rank."""
import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

_COLS = "code, brand, name, per100, pack_cents, amount, unit, price_date, price_stale, chains, scans"


class AltIndex:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None
        self._sig = None
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
                except sqlite3.Error:
                    self._conn = None
            return self._conn

    def available(self) -> bool:
        c = self._c()
        if c is None:
            return False
        with self._lock:
            try:
                return c.execute("select 1 from alt limit 1").fetchone() is not None
            except sqlite3.Error:
                return False

    def candidates(self, tags: List[str], type_id: Optional[str] = None, groups: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Every eligible product in the scanned product's categories: its OFF category tags, its Mieux type and its 1000+ taxonomy groups.
        Retrieval is deliberately broad; taxonomy.substitution decides what is comparable afterwards."""
        c = self._c()
        if c is None:
            return []
        parts, args = [], []
        if tags:
            parts.append("select code from alt_cat where tag in (%s)" % ",".join("?" * len(tags)))
            args += tags
        if type_id:
            parts.append("select code from alt where type = ?")
            args.append(type_id)
        if groups:
            parts.append("select code from alt_tax where grp in (%s)" % ",".join("?" * len(groups)))
            args += groups
        if not parts:
            return []
        sql = f"select {_COLS} from alt where code in ({' union '.join(parts)})"
        with self._lock:
            try:
                rows = c.execute(sql, tuple(args)).fetchall()
            except sqlite3.Error:
                return []
        out = []
        for code, brand, name, per100, pack, amount, unit, date, stale, chains, scans in rows:
            out.append({"code": code, "brand": brand, "name": name, "per100_cents": per100, "pack_cents": pack,
                        "quantity": {"amount": amount, "unit": unit}, "price_date": date, "price_stale": bool(stale),
                        "chains": json.loads(chains or "[]"), "scans": scans or 0})
        return out
