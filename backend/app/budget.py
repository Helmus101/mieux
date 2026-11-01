"""Budget & savings logic (pure functions, easy to test). Money is integer cents. Dates are ISO strings."""
import calendar
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

PERIODS = ("weekly", "monthly", "per_trip")
STYLES = ("stay", "balanced", "nutrition")  # stay within budget | save without compromising too much | best nutrition


def window(period: str, today: date, back: int = 0) -> Tuple[date, date]:
    """[start, end] of the current (back=0) or an earlier period."""
    if period == "monthly":
        y, m = today.year, today.month - back
        while m <= 0:
            m += 12; y -= 1
        return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=back)
    return start, start + timedelta(days=6)


def elapsed_fraction(period: str, today: date) -> Optional[float]:
    if period == "weekly":
        return (today.weekday() + 1) / 7
    if period == "monthly":
        return today.day / calendar.monthrange(today.year, today.month)[1]
    return None


def _d(s: Optional[str]) -> Optional[date]:
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def spent_in(receipts: List[Dict[str, Any]], start: date, end: date) -> int:
    return sum(r["total_cents"] or 0 for r in receipts if (d := _d(r["date"])) and start <= d <= end)


def status(period: str, budget_cents: int, receipts: List[Dict[str, Any]], today: date) -> Dict[str, Any]:
    if period == "per_trip":
        last = max((r for r in receipts if _d(r["date"])), key=lambda r: r["date"], default=None)
        spent = last["total_cents"] if last else 0
        start = end = _d(last["date"]) if last else today
        frac = None
    else:
        start, end = window(period, today)
        spent = spent_in(receipts, start, end)
        frac = elapsed_fraction(period, today)
    used = spent / budget_cents if budget_cents else 0.0
    if used > 1:
        label = "over"
    elif used >= 0.85 or (frac is not None and used > frac * 1.1 + 0.05):
        label = "watch"
    else:
        label = "on_track"
    # earlier periods -> your usual spending, and a realistic suggestion
    prev = []
    if period != "per_trip":
        for b in range(1, 5):
            s0, e0 = window(period, today, b)
            prev.append(spent_in(receipts, s0, e0))
    usual = round(sum(prev) / len([p for p in prev if p > 0])) if any(p > 0 for p in prev) else None
    suggestion = None
    if usual and budget_cents and abs(usual - budget_cents) / budget_cents > 0.15:
        suggestion = int(round(usual * 0.95 / 500.0) * 500)  # 5% under what you actually spend, rounded to 5 EUR
    days_total = (end - start).days + 1
    days_elapsed = max(1, min(days_total, (today - start).days + 1)) if period != "per_trip" else None
    n_receipts = sum(1 for r in receipts if (d := _d(r["date"])) and start <= d <= end)
    fc = None
    if days_elapsed and n_receipts >= 2 and days_elapsed >= 2:  # a projection needs some data; it is an estimate, not a certainty
        daily = spent / days_elapsed
        left = max(0, days_total - days_elapsed)
        fc = {"daily_avg_cents": round(daily), "days_left": left, "projected_cents": round(daily * days_total),
              "required_daily_cents": round(max(0, budget_cents - spent) / left) if left else None, "will_exceed": daily * days_total > budget_cents, "kind": "estimate", "receipts": n_receipts}
    return {"forecast": fc, "period": period, "start": start.isoformat(), "end": end.isoformat(), "budget_cents": budget_cents, "spent_cents": spent,
            "remaining_cents": budget_cents - spent, "used_pct": round(used * 100, 1), "elapsed_pct": None if frac is None else round(frac * 100),
            "label": label, "usual_cents": usual, "previous_cents": prev[0] if prev else None, "suggested_budget_cents": suggestion}


def pressure(st: Dict[str, Any]) -> str:
    """How constrained the user is right now: relaxed | tight | over."""
    if st["used_pct"] > 100:
        return "over"
    if st["label"] == "watch" or st["remaining_cents"] <= st["budget_cents"] * 0.2:
        return "tight"
    return "relaxed"


def recommended_ranking(style: str, press: str) -> str:
    """Which of the three rankings to show first. Cheap when money is short, nutrition when there is room."""
    if press == "over":
        return "budget"
    if style == "stay":
        return "budget" if press == "tight" else "value"
    if style == "nutrition":
        return "value" if press == "tight" else "match"
    return "budget" if press == "tight" else "value"  # balanced


def category_changes(this: Dict[str, int], before: Dict[str, int], min_before: int = 500, threshold: float = 0.15) -> List[Dict[str, Any]]:
    out = []
    for cat, now in this.items():
        was = before.get(cat, 0)
        if was >= min_before:
            ch = (now - was) / was
            if abs(ch) >= threshold:
                out.append({"category": cat, "change_pct": round(ch * 100), "now_cents": now, "before_cents": was})
    return sorted(out, key=lambda x: -abs(x["change_pct"]))[:3]


GROUPS = [  # broad groups for category budgets, matched by substring on Open Food Facts category tags (first match wins)
    ("drinks", ["beverage", "drink", "water", "juice", "soda", "tea", "coffee", "wine", "beer"]),
    ("dairy", ["dairies", "dairy", "yogurt", "milk", "cheese", "butter", "cream"]),
    ("meat_fish", ["meat", "fish", "seafood", "poultry", "ham", "sausage", "charcuterie"]),
    ("fruit_veg", ["fruit", "vegetable", "legume", "salad", "potato"]),
    ("snacks_sweets", ["snack", "biscuit", "cookie", "chocolate", "candy", "confectioner", "sweet", "cake", "chips", "dessert", "spread"]),
    ("bakery_cereals", ["bread", "cereal", "pasta", "rice", "flour", "bakery", "pastr"]),
]


def category_group(tags: List[str]) -> str:
    joined = " ".join(tags).lower()
    for name, keys in GROUPS:
        if any(k in joined for k in keys):
            return name
    return "other"
