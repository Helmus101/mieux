import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402

c = TestClient(main.app)


def test_a_report_is_logged_and_answered_without_a_body(caplog):
    with caplog.at_level(logging.WARNING, logger=main.logger.name):
        r = c.post("/v1/client-errors", json={"message": "boom", "stack": "Error: boom\n  at x", "url": "/app/scan", "version": "1.0.0+abc", "kind": "chunk"})
    assert r.status_code == 204
    assert r.content == b""
    line = next(m for m in caplog.messages if m.startswith("client_error"))
    assert "kind=chunk" in line and "version=1.0.0+abc" in line and "'boom'" in line
    assert "\n" not in line  # one line per report, so logs stay greppable


def test_reports_are_validated():
    assert c.post("/v1/client-errors", json={"message": ""}).status_code == 422
    assert c.post("/v1/client-errors", json={"message": "x" * 601}).status_code == 422
    assert c.post("/v1/client-errors", json={"message": "x", "kind": "weird"}).status_code == 422
