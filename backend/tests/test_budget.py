import os, sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from app import budget as B  # noqa: E402

TODAY = date(2026, 10, 29)  # Thursday
R = lambda d, c: {"date": d, "total_cents": c}  # noqa: E731


def test_windows_and_status_weekly():
    assert B.window("weekly", TODAY) == (date(2026, 10, 26), date(2026, 11, 1))
    assert B.window("monthly", TODAY) == (date(2026, 10, 1), date(2026, 10, 31))
    assert B.window("monthly", date(2026, 1, 5), 1) == (date(2025, 12, 1), date(2025, 12, 31))
    st = B.status("weekly", 10000, [R("2026-10-27", 6240), R("2026-10-20", 8000)], TODAY)
    assert st["spent_cents"] == 6240 and st["remaining_cents"] == 3760 and st["used_pct"] == 62.4
    assert st["label"] == "on_track"                                           # Thursday = 4/7 of the week, 62% is fine
    assert B.status("weekly", 10000, [R("2026-10-27", 9000)], TODAY)["label"] == "watch"
    assert B.status("weekly", 10000, [R("2026-10-27", 12000)], TODAY)["label"] == "over"


def test_learning_and_suggestion():
    rows = [R("2026-10-27", 3000), R("2026-10-20", 5000), R("2026-10-13", 5000), R("2026-10-06", 5000), R("2026-09-29", 5000)]
    st = B.status("weekly", 10000, rows, TODAY)
    assert st["usual_cents"] == 5000 and st["suggested_budget_cents"] == 5000      # 95% of 50 EUR rounded to 5 EUR
    assert B.status("weekly", 5000, rows, TODAY)["suggested_budget_cents"] is None  # budget already realistic


def test_per_trip_and_recommendation_adapts():
    st = B.status("per_trip", 3000, [R("2026-10-25", 2000), R("2026-10-28", 2500)], TODAY)
    assert st["spent_cents"] == 2500 and st["remaining_cents"] == 500
    plenty = B.status("weekly", 10000, [R("2026-10-27", 1000)], TODAY)
    short = B.status("weekly", 10000, [R("2026-10-27", 9000)], TODAY)
    assert B.pressure(plenty) == "relaxed" and B.pressure(short) == "tight"
    assert B.recommended_ranking("balanced", "relaxed") == "value" and B.recommended_ranking("balanced", "tight") == "budget"
    assert B.recommended_ranking("nutrition", "relaxed") == "match" and B.recommended_ranking("stay", "relaxed") == "value"
    assert B.recommended_ranking("nutrition", "over") == "budget"


def test_category_changes():
    ch = B.category_changes({"dairy": 1180, "meat": 2000}, {"dairy": 1000, "meat": 2000, "snacks": 100})
    assert ch == [{"category": "dairy", "change_pct": 18, "now_cents": 1180, "before_cents": 1000}]


def test_forecast_needs_data_and_is_an_estimate():
    rows = [R("2026-10-26", 4000), R("2026-10-28", 4000)]
    f = B.status("weekly", 10000, rows, TODAY)["forecast"]                      # Thursday: 4 of 7 days elapsed, 80 EUR spent
    assert f["kind"] == "estimate" and f["daily_avg_cents"] == 2000 and f["days_left"] == 3
    assert f["projected_cents"] == 14000 and f["will_exceed"] is True and f["required_daily_cents"] == 667
    assert B.status("weekly", 10000, [R("2026-10-28", 4000)], TODAY)["forecast"] is None   # one receipt is not enough
    assert B.status("per_trip", 3000, rows, TODAY)["forecast"] is None


def test_category_groups():
    assert B.category_group(["en:dairies", "en:yogurts"]) == "dairy"
    assert B.category_group(["en:beverages", "en:waters"]) == "drinks"
    assert B.category_group(["en:snacks", "en:sweet-snacks"]) == "snacks_sweets"
    assert B.category_group(["en:something-else"]) == "other"
