collect_ignore = ["load_test.py"]


import pytest


@pytest.fixture(autouse=True)
def _no_live_web_search(monkeypatch):
    """Tests never call the live search API (importing main loads the real .env keys)."""
    for k in ("DEEPSEEK_API_KEY", "PARALLEL_API_KEY", "LANGSEARCH_API_KEY", "GEMINI_API_KEY", "BRAVE_API_KEY", "SERPER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("WEBPRICE_PARALLEL", "1")   # tests of the provider order exercise Parallel when its key is set; production leaves it off
    # The daily search/AI-call budgets are plain module-level dicts, shared mutable state across the whole pytest
    # process: whichever test happens to run first "spends" them for every test after it, in whatever order the
    # runner picks. Reset both before every test so no test's pass/fail depends on execution order.
    from app import webprice
    webprice._day.update(d="", n=0)
    webprice._ai_day.update(d="", n=0)
