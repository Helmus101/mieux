import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app import main, vision  # noqa: E402

c = TestClient(main.app)
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0fake-jpeg").decode()
H = {"X-Beta": "1", "X-Session-Id": "vision-test-1"}


class FakeOFF:
    """Stands in for the product database."""
    def __init__(self, rows, exact=None):
        self.rows, self.exact = rows, exact or {}

    def search_name(self, q):
        return self.rows

    def get_product(self, code):
        return self.exact.get(code)


HUMMUS = {"code": "3760059041450", "product_name": "Houmous Authentique", "brands": "Saladinettes", "quantity": "200 g", "image_front_small_url": "http://x/y.jpg"}
OTHER = {"code": "111", "product_name": "Tomates pelées", "brands": "Cirio", "quantity": "400 g"}


def ident(**kw):
    return {"identified": True, "brand": "Saladinettes", "product_name": "Houmous Authentique", "variant": "", "size": "200 g", "barcode_digits": "", "confidence": "high", **kw}


def test_barcode_checksum():
    assert vision.valid_barcode("3760059041450")
    assert vision.valid_barcode("5449000000996")
    assert not vision.valid_barcode("3760059041451")   # wrong check digit
    assert not vision.valid_barcode("12345")


def test_match_ranks_the_right_product_first_and_drops_unrelated_ones():
    out = vision.match(FakeOFF([OTHER, HUMMUS]), ident())
    assert [m["barcode"] for m in out] == ["3760059041450"]
    assert out[0]["match"] > 0.9 and out[0]["brand"] == "Saladinettes" and out[0]["exact"] is False


def test_match_is_accent_and_case_insensitive_and_checks_the_pack_size():
    p = {**HUMMUS, "product_name": "HOUMOUS AUTHENTIQUÉ"}
    right = vision.match(FakeOFF([p]), ident(size="200 g"))[0]["match"]
    wrong = vision.match(FakeOFF([p]), ident(size="1 kg"))[0]["match"]
    assert right > wrong


def test_a_legible_valid_barcode_found_in_the_database_is_an_exact_hit():
    db = FakeOFF([], exact={"3760059041450": HUMMUS})
    out = vision.match(db, ident(identified=False, brand="", product_name="", barcode_digits="3760 0590 41450"))
    assert out and out[0]["barcode"] == "3760059041450" and out[0]["exact"] is True


def test_a_barcode_with_a_bad_checksum_is_never_trusted():
    db = FakeOFF([], exact={"3760059041451": HUMMUS})
    assert vision.match(db, ident(identified=False, brand="", product_name="", barcode_digits="3760059041451")) == []


def test_not_a_product_returns_nothing():
    assert vision.match(FakeOFF([HUMMUS]), {**ident(), "identified": False, "brand": "", "product_name": ""}) == []


def test_endpoint_is_closed_without_the_beta_header():
    r = c.post("/v1/vision/identify", json={"image": JPEG}, headers={"X-Session-Id": "vision-test-2"})
    assert r.status_code == 403


def test_endpoint_rejects_bad_input():
    assert c.post("/v1/vision/identify", json={"image": JPEG, "media_type": "application/pdf"}, headers=H).status_code == 422
    assert c.post("/v1/vision/identify", json={"image": "not base64 !!"}, headers=H).status_code == 422


def test_endpoint_says_503_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert c.post("/v1/vision/identify", json={"image": JPEG}, headers=H).status_code == 503


def test_endpoint_returns_identification_and_barcode_matches(monkeypatch):
    monkeypatch.setattr(vision, "identify", lambda img, mt: ident())
    monkeypatch.setattr(main.app.state, "off", FakeOFF([HUMMUS, OTHER]))
    r = c.post("/v1/vision/identify", json={"image": JPEG}, headers=H)
    assert r.status_code == 200
    j = r.json()
    assert j["identified"] is True and j["brand"] == "Saladinettes" and j["name"] == "Houmous Authentique"
    assert [m["barcode"] for m in j["matches"]] == ["3760059041450"]


def test_endpoint_hides_sdk_errors(monkeypatch):
    def boom(img, mt):
        raise ValueError("secret detail")
    monkeypatch.setattr(vision, "identify", boom)
    r = c.post("/v1/vision/identify", json={"image": JPEG}, headers=H)
    assert r.status_code == 502 and "secret" not in r.text
