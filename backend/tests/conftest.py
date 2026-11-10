collect_ignore = ["load_test.py"]


import pytest


@pytest.fixture(autouse=True)
def _no_live_web_search(monkeypatch):
    """Tests never call the live search API (importing main loads the real .env keys)."""
    for k in ("PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "GEMINI_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("WEBPRICE_PARALLEL", "1")   # tests of the provider order exercise Parallel when its key is set; production leaves it off
