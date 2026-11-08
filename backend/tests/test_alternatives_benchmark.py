import pytest
from datetime import date, timedelta
from app import engine, taxonomy, value
from app.products import normalize


def make_product(barcode, name, brand="Brand", categories=None, score=70, sold=True, quantity_g=500, **nutriments):
    cats = categories if categories is not None else ["en:dairies", "en:yogurts", "en:plain-yogurts"]
    default_nutri = {
        "energyKcal100g": 80,
        "fat100g": 3.0,
        "saturatedFat100g": 1.5,
        "carbohydrates100g": 5.0,
        "sugars100g": 4.5,
        "protein100g": 5.0,
        "fiber100g": 0.0,
        "salt100g": 0.1,
    }
    default_nutri.update(nutriments)
    return {
        "barcode": barcode,
        "id": barcode,
        "name": name,
        "brand": brand,
        "categories": cats,
        "soldInFrance": sold,
        "allergens": [],
        "traces": [],
        "ingredientsText": "lait",
        "analysis": [],
        "nutriments": default_nutri,
        "score": {"total": score},
        "nutriScore": "a" if score >= 80 else "b" if score >= 60 else "c",
        "additives": [],
        "quantity": {"amount": quantity_g, "unit": "g"},
        "dataQuality": {"nutritionComplete": True},
    }


# =====================================================================
# 1. RETRIEVAL & REMOVAL OF DESTRUCTIVE PRE-FILTER
# =====================================================================

def test_prefilter_does_not_truncate_candidates():
    """Candidates beyond index 120 must not be discarded before price lookup."""
    orig = make_product("000", "Original Yogurt", score=65)
    # Generate 150 valid peers
    peers = [make_product(f"bc_{i:03d}", f"Yogurt {i}", score=60 + (i % 20)) for i in range(1, 151)]
    # prefilter without an arbitrary limit should return all 150 candidates
    filtered = engine.prefilter(orig, peers, [], None, "similar")
    assert len(filtered) == 150
    assert any(c["barcode"] == "bc_149" for c in filtered)


def test_categoryless_candidate_allowed_when_name_supports_classification():
    """A candidate with empty categories_tags must not be rejected if name allows classification."""
    from app.main import _raw_candidate
    orig = make_product("000", "Yaourt nature", categories=["en:yogurts"])
    raw_with_classifiable_name = {
        "product_name": "Yaourt nature fermier",
        "brands": "Ferme Bio",
        "categories_tags": [],
        "countries_tags": ["en:france"],
    }
    raw_unclassifiable = {
        "product_name": "Produit Inconnu XYZ 123",
        "brands": "Mystère",
        "categories_tags": [],
        "countries_tags": ["en:france"],
    }
    assert _raw_candidate(raw_with_classifiable_name, [], [], orig) is True
    assert _raw_candidate(raw_unclassifiable, [], [], orig) is False


# =====================================================================
# 2. PRODUCT COMPARABILITY & SUBSTITUTION LEVELS
# =====================================================================

def test_cheapest_and_value_allow_only_substitution_levels_1_and_2():
    """Cheapest and Best Value must reject substitution levels 3 and 4, even if cheap or high quality."""
    orig = make_product("000", "Biscottes complètes", categories=["en:breads", "en:rusks"], score=70)
    
    # Level 1 substitute (another rusk)
    lvl1 = make_product("001", "Biscottes 6 céréales", categories=["en:breads", "en:rusks"], score=72)
    # Level 2 substitute (toasted bread)
    lvl2 = make_product("002", "Pain grillé Pelletier", categories=["en:breads", "en:toasts"], score=71)
    # Level 3 substitute (sliced brioche)
    lvl3 = make_product("003", "Brioche tranchée", categories=["en:breads", "en:brioches", "en:sliced-breads"], score=75)
    # Level 4 substitute (sandwich bread)
    lvl4 = make_product("004", "Pain de mie nature", categories=["en:breads", "en:sliced-breads"], score=75)
    
    pool = [lvl1, lvl2, lvl3, lvl4]
    prices = {"001": 25.0, "002": 26.0, "003": 15.0, "004": 10.0}  # Level 3 and 4 are cheaper!
    
    rankings = engine.build_rankings(orig, pool, prices, orig_price=40.0, priorities=["value"], mode="similar", lang="fr", match_list=[])
    
    budget_barcodes = {r["product"]["barcode"] for r in rankings["budget"]}
    value_barcodes = {r["product"]["barcode"] for r in rankings["value"]}
    
    # Levels 3 and 4 must NEVER win Cheapest or Best Value
    assert "003" not in budget_barcodes
    assert "004" not in budget_barcodes
    assert "003" not in value_barcodes
    assert "004" not in value_barcodes
    
    # Levels 1 and 2 are eligible
    assert "001" in budget_barcodes
    assert "002" in budget_barcodes


def test_similarity_score_does_not_exclude_same_type_substitutes():
    """A genuine substitute of the same type (level 1-2) must not be dropped for low deep_similarity."""
    orig = make_product("000", "Plain Greek Yogurt Original", brand="Fage",
                        categories=["en:foods", "en:dairies", "en:fermented-foods", "en:fermented-milk-products", "en:yogurts", "en:plain-yogurts"],
                        score=70, quantity_g=1000, energyKcal100g=130, fat100g=10, carbohydrates100g=4, protein100g=9)
    # Different tags except leaf, completely different words, macro divergence, pack size 100g vs 1000g -> sim < 0.45
    cand = make_product("001", "Spécialité égouttée", brand="Autre",
                        categories=["en:fresh-foods", "en:plain-yogurts"],
                        score=68, quantity_g=100, energyKcal100g=50, fat100g=0.5, carbohydrates100g=15, protein100g=2)
    
    sim = engine.deep_similarity(orig, cand)
    assert sim < 0.45  # Low similarity!
    
    # Despite low similarity, because it is level 1 (same leaf category), it must still be accepted and ranked
    prices = {"001": 20.0}
    rankings = engine.build_rankings(orig, [cand], prices, orig_price=40.0, priorities=["budget"], mode="similar", lang="fr", match_list=[])
    assert len(rankings["budget"]) == 1
    assert rankings["budget"][0]["product"]["barcode"] == "001"


# =====================================================================
# 3. PRICE ENGINE & FRESHNESS POLICY
# =====================================================================

def test_stale_and_estimated_prices_rejected_from_cheapest_and_value():
    """Only observed prices from <= 90 days can qualify for Cheapest or Best Value."""
    orig = make_product("000", "Yaourt nature", score=65)
    fresh_p = make_product("001", "Yaourt Fresh", score=66)
    stale_p = make_product("002", "Yaourt Stale", score=66)
    est_p = make_product("003", "Yaourt Estimated", score=66)
    
    today = date.today()
    points = {
        "001": {"source": "open_prices", "date": (today - timedelta(days=20)).isoformat(), "stale": False},
        "002": {"source": "open_prices", "date": (today - timedelta(days=120)).isoformat(), "stale": True},
        "003": {"source": "estimate", "date": None, "stale": False},
    }
    prices = {"001": 30.0, "002": 15.0, "003": 10.0}  # Stale and estimate are cheaper
    
    rankings = engine.build_rankings(orig, [fresh_p, stale_p, est_p], prices, orig_price=50.0,
                                     priorities=["budget", "value"], mode="similar", lang="fr",
                                     match_list=[], estimated=frozenset({"003"}), points=points)
    
    budget_barcodes = {r["product"]["barcode"] for r in rankings["budget"]}
    value_barcodes = {r["product"]["barcode"] for r in rankings["value"]}
    
    assert "001" in budget_barcodes
    assert "002" not in budget_barcodes  # Stale (>90 days) rejected
    assert "003" not in budget_barcodes  # Estimate rejected
    assert "002" not in value_barcodes
    assert "003" not in value_barcodes


# =====================================================================
# 4. RANKING ENGINES: CHEAPEST, QUALITY, BEST VALUE
# =====================================================================

def test_cheapest_enforces_quality_floor_and_no_fillers():
    """Cheapest must enforce candidate score >= original score - 5 and never pad with non-cheaper fillers."""
    orig = make_product("000", "Yaourt nature", score=70)
    
    cheap_good = make_product("001", "Yaourt Éco Bon", score=66)     # 70 - 4 >= 65: OK
    cheap_bad = make_product("002", "Yaourt Éco Mauvais", score=55)  # 70 - 15 < 65: Fails quality floor
    expensive = make_product("003", "Yaourt Cher", score=80)         # More expensive than orig
    
    prices = {"001": 25.0, "002": 15.0, "003": 65.0}
    
    res = engine.rank_cheapest(orig, [cheap_good, cheap_bad, expensive], prices, orig_price=50.0)
    items = res["items"]
    
    assert len(items) == 1
    assert items[0]["product"]["barcode"] == "001"
    # Never filled to 5 with not_cheaper items!


def test_quality_ranking_is_strictly_by_score_and_labels_who_is_better():
    """Every scored close substitute is listed in strict score order; only those at least 5 points higher are flagged as better."""
    orig = make_product("000", "Yaourt nature", score=70)

    better1 = make_product("001", "Yaourt Supérieur", score=85)
    better2 = make_product("002", "Yaourt Élite", score=80)
    worse = make_product("003", "Yaourt Ordinaire", score=68)
    equal = make_product("004", "Yaourt Équivalent", score=70)

    res = engine.rank_quality(orig, [worse, better2, equal, better1])
    assert [r["product"]["barcode"] for r in res] == ["001", "002", "004", "003"]          # strictly by score, whatever the input order
    assert [r["better"] for r in res] == [True, True, False, False]
    assert [r["quality_delta"] for r in res] == [15, 10, 0, -2]


def test_quality_ranking_lists_one_pack_size_once_and_ignores_price():
    orig = make_product("000", "Yaourt nature", score=70)
    a = make_product("001", "Yaourt Supérieur", score=85)
    b = make_product("002", "Yaourt Supérieur", score=85)         # same product, another barcode
    c = make_product("003", "Yaourt Élite", score=80)
    cheap_first = engine.rank_quality(orig, [a, b, c], {"001": 900.0, "003": 10.0})
    assert [r["product"]["barcode"] for r in cheap_first] == ["001", "003"]


def test_best_value_percentile_and_pareto_frontier():
    """Best value uses percentile geometric mean and deprioritizes dominated options."""
    orig = make_product("000", "Yaourt Standard", score=65)
    
    # Product A: quality 82, price 20 cents
    prod_a = make_product("001", "Produit A", score=82)
    # Product B: quality 82, price 16 cents (DOMINATES A!)
    prod_b = make_product("002", "Produit B", score=82)
    # Product C: quality 88, price 25 cents (Not dominated)
    prod_c = make_product("003", "Produit C", score=88)
    
    prices = {"001": 20.0, "002": 16.0, "003": 25.0}
    
    res = engine.rank_best_value(orig, [prod_a, prod_b, prod_c], prices, orig_price=30.0)
    items = res["items"]
    
    assert len(items) == 3
    # Check that Product A is marked as dominated by Product B
    item_map = {r["product"]["barcode"]: r for r in items}
    assert item_map["001"]["dominated"] is True
    assert item_map["002"]["dominated"] is False
    assert item_map["003"]["dominated"] is False
    
    # Non-dominated items (002, 003) must come before dominated item (001)
    barcodes_order = [r["product"]["barcode"] for r in items]
    assert barcodes_order.index("002") < barcodes_order.index("001")
    assert barcodes_order.index("003") < barcodes_order.index("001")
    
    # Exposes percentile metrics
    for item in items:
        assert "quality_percentile" in item
        assert "affordability_percentile" in item
        assert "value_score" in item
        assert 1 <= item["value_score"] <= 100


def test_missing_original_price_sets_no_baseline_honestly():
    """When scanned product has no verified price, rankings report no_baseline=True without false saving claims."""
    orig = make_product("000", "Yaourt Sans Prix", score=65)
    cand1 = make_product("001", "Yaourt A", score=70)
    cand2 = make_product("002", "Yaourt B", score=68)
    
    prices = {"001": 22.0, "002": 28.0}
    rankings = engine.build_rankings(orig, [cand1, cand2], prices, orig_price=None, priorities=["value"], mode="similar", lang="fr", match_list=[])
    
    assert rankings["no_baseline"] is True
    assert len(rankings["budget"]) == 2
    # Verify why text explains comparison is among known prices, not savings against scanned
    assert "inconnu" in rankings["budget"][0]["why"].lower() or "directe" in rankings["budget"][0]["why"].lower()
