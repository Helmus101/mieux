# Alternatives: independent evaluation

**What is verified.** `backend/tests/data/reference_pairs.json` holds 121 product pairs (about 60 valid swaps, 56 look-alikes that must be refused, plus a few "variant" pairs that are reported but never counted). They are labelled by what a shopper would accept, not by what `taxonomy.substitution()` returns. `backend/tests/test_reference_pairs.py` fails CI if a known bad pair is accepted (level 1-2, both directions) or a known good pair refused. `backend/scripts/eval_reference.py` prints precision, recall and every false positive/negative.

**How to extend it.** Add a row to `backend/tests/data/gen_reference.py` for every wrong alternative a user reports, re-run it, then fix the rule until the suite is green.

**Limits - read before claiming accuracy.**
- The labels were written by one author (an AI assistant working with the maintainer), not by two independent humans. They are not human-verified.
- The pairs are synthetic names plus plausible category tags, not real barcodes; they test the compatibility gate (`taxonomy.substitution`), not retrieval, ranking, prices or the UI.
- The rules were then fixed until this set passed, so 100% on it is a regression gate, not a measure of real-world accuracy. A fresh, unseen set is needed for that.
- Next steps: label real Open Food Facts barcodes (France: Carrefour, Leclerc, Lidl, Auchan, Monoprix), have two people label the hard cases, measure precision@5/@10 and recall on the live endpoint, and track the numbers per release.
