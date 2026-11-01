import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
from app import explain as E  # noqa: E402

F = {"original": "Yaourt fruits", "alternative": "Skyr nature", "protein_diff": 6.0, "sugars_diff": -7.0, "fibre_diff": 0.3, "salt_diff": 0.0, "sat_fat_diff": -1.6, "kcal_diff": -20,
     "nova_original": 3, "nova_alternative": 3, "price_per_kg_original": 5.0, "price_per_kg_alternative": 4.1, "price_diff_pct": -18}


class Fake:
    def __init__(self, out): self.out, self.calls = out, 0
    def complete(self, system, user):
        self.calls += 1
        return self.out


def test_template_only_uses_fact_numbers_fr_and_en():
    fr, en = E.template(F, "fr"), E.template(F, "en")
    assert "18 % moins cher" in fr and "6 g de protéines en plus" in fr and "7 g de sucres en moins" in fr and "5 €" in fr
    assert "18% less per kg" in en and "6 g more protein" in en
    assert E.valid(fr, F) and E.valid(en, F)


def test_llm_text_with_only_known_numbers_is_accepted():
    r = E.explain(F, "fr", Fake("Le skyr coûte 18 % moins cher au kilo, avec 6 g de protéines en plus pour 100 g."))
    assert r["source"] == "llm" and "18 %" in r["text"]


def test_llm_invented_number_is_rejected_and_template_used():
    r = E.explain(F, "fr", Fake("Le skyr coûte 25 % moins cher et contient 12 g de protéines en plus."))
    assert r["source"] == "template" and r["llm_rejected"] and "18 %" in r["text"]


def test_llm_health_claim_is_rejected():
    r = E.explain(F, "fr", Fake("Le skyr est moins cher de 18 % et protège du cancer."))
    assert r["source"] == "template" and r["llm_rejected"]


def test_no_llm_or_failing_llm_falls_back_to_template():
    assert E.explain(F, "fr", None)["source"] == "template"
    assert E.explain(F, "fr", Fake(None))["source"] == "template"


def test_missing_data_is_said_not_invented():
    f = {"original": "A", "alternative": "B", "protein_diff": None, "sugars_diff": None, "fibre_diff": None, "salt_diff": None, "sat_fat_diff": None, "kcal_diff": None}
    assert "ne permettent pas" in E.template(f, "fr")


def test_endpoint_returns_template_without_key_and_uses_llm_when_valid():
    from fastapi.testclient import TestClient
    from datetime import date
    import test_all as TA                                                      # reuse the fake Open Food Facts app
    TA.main.app.state.prices = type("P", (), {"latest": lambda self, b, q, *a: {"source": "open_prices", "per100_cents": {"1": 50.0, "2": 30.0}.get(b, 90.0), "date": date.today().isoformat(), "where": None}})()
    for r in TA.main.app.state.off.items.values(): r["quantity"] = "400 g"
    s = TA.main.app.state.sessions(); s.query(TA.db.Product).delete(); s.commit()
    H = {"X-Session-Id": "explain-user-001", "X-Lang": "fr"}
    TA.main.app.state.llm = None
    r = TA.c.post("/v1/explain", headers=H, json={"original_id": "1", "alt_id": "2"}).json()
    assert r["source"] == "template" and "40 % moins cher" in r["text"] and r["facts"]["price_per_kg_alternative"] == 3.0
    TA.main.app.state.llm = Fake("Skyr nature coûte 40 % moins cher au kilo que Strawberry yogurt.")
    r = TA.c.post("/v1/explain", headers=H, json={"original_id": "1", "alt_id": "2"}).json()
    assert r["source"] == "llm"
    TA.main.app.state.llm = Fake("Il coûte 99 % moins cher.")
    assert TA.c.post("/v1/explain", headers=H, json={"original_id": "1", "alt_id": "2"}).json()["source"] == "template"
    TA.main.app.state.llm = None
