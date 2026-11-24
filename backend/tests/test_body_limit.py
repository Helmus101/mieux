from fastapi.testclient import TestClient
from app.main import app


def test_oversized_body_is_refused():
    r = TestClient(app).post("/v1/errors", content=b"x" * 1_100_000, headers={"content-type": "application/json"})
    assert r.status_code == 413
