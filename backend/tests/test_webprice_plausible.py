from app import webprice, value_index


def _prod(type_name_hint="Prince biscuits chocolat"):
    return {"barcode": "7622210449283", "name": type_name_hint, "brand": "Lu", "quantity": {"amount": 300.0, "unit": "g"}, "categories_tags": ["en:biscuits"]}


def _w(per100, urls=("https://www.carrefour.fr/p/x",)):
    return {"per100_cents": per100, "pack_cents": round(per100 * 3), "source_urls": list(urls)}


def test_foreign_domain_only_is_dropped(monkeypatch):
    monkeypatch.setattr(value_index, "_load", lambda: {})
    p = _prod()
    assert webprice._plausible(p, _w(150, ("https://www.mega-einkaufsparadies.de/fr/lindt",))) is None
    assert webprice._plausible(p, _w(150, ("https://www.mega-einkaufsparadies.de/x", "https://www.carrefour.fr/x"))) is not None


def test_outlier_unit_price_is_dropped(monkeypatch):
    from app import taxonomy
    monkeypatch.setattr(taxonomy, "classify", lambda p: {"type": "sweet_biscuits"})
    monkeypatch.setattr(value_index, "_load", lambda: {"sweet_biscuits": {"n": 50, "price_q": [20, 60, 100, 150, 200, 300, 600]}})
    p = _prod()
    assert webprice._plausible(p, _w(1833)) is None          # 55 EUR for 300 g of biscuits
    assert webprice._plausible(p, _w(2)) is None             # 0.06 EUR for 300 g
    assert webprice._plausible(p, _w(95)) is not None
    assert webprice._plausible(p, _w(480)) is not None       # dear but real


def test_store_only_result_passes(monkeypatch):
    monkeypatch.setattr(value_index, "_load", lambda: {})
    w = {"per100_cents": None, "pack_cents": None, "stores": ["Carrefour"], "no_price": True}
    assert webprice._plausible(_prod(), w) is w
    assert webprice._plausible(_prod(), None) is None
