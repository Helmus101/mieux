"""Permanent gate: every pair in tests/data/reference_pairs.json (labelled from shopper logic, independent of the taxonomy rules)
must come out as labelled. A change that accepts a known bad alternative, or refuses a known good one, fails here.
Add a pair to tests/data/gen_reference.py (and re-run it) for every wrong alternative a user reports."""
import json, os
import pytest
from app import taxonomy

_PATH = os.path.join(os.path.dirname(__file__), "data", "reference_pairs.json")
_ROWS = [r for r in json.load(open(_PATH)) if r["label"] in ("valid", "invalid")]


def _accepted(a, b):
    ab, ba = taxonomy.substitution(a, b), taxonomy.substitution(b, a)
    return bool(ab and ba and ab["level"] <= 2 and ba["level"] <= 2)


@pytest.mark.parametrize("row", _ROWS, ids=lambda r: r["why"])
def test_reference_pair(row):
    assert _accepted(row["a"], row["b"]) == (row["label"] == "valid"), f'{row["a"]["name"]} <-> {row["b"]["name"]}'


def test_reference_set_is_balanced_and_large_enough():
    labels = [r["label"] for r in _ROWS]
    assert len(labels) >= 100 and labels.count("invalid") >= 40 and labels.count("valid") >= 40
