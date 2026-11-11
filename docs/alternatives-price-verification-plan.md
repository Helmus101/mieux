# Alternatives and price verification plan

**Status:** active
**Scope:** the whole path from a scanned barcode to the alternatives shown in Valeur / Qualité, including candidate retrieval, the France gate, compatibility, ranking, price resolution and display.
**Goal:** prove the app finds as many real alternatives as the local data allows, that every recommendation is genuinely sold in France, and that every price is accurate, sourced and labelled. Fix only what the measurements prove.

## Baseline measured on 11 November 2026

| Product | Category (most specific) | Quick rows | Candidates retrieved | Verified prices | Latency |
|---|---:|---:|---:|---:|---:|
| Mini saucisson sec | dry-sausage-pure-pork 439 / dry-sausages 2,350 | 2,350 | **591** | 107 | 4.0 s |
| Pizza sticks | salty-snacks 15,362 | 15,362 | 171 | 123 | 4.8 s |
| Mini-toasts sésame | crackers-appetizers 3,527 | 3,527 | 330 | 172 | 3.3 s |
| Tomate séchée spread | spreads 42,760 | 42,760 | 114 | 40 | 2.6 s |
| Chocolat noir 70 % | dark-chocolates 5,681 | 5,681 | **575** | 207 | 4.3 s |
| Galettes riz bio | puffed-wholegrain-rice-cakes 108 | 108 | 82 | 13 | 2.4 s |

Findings:

- **The retrieval cap is binding.** `PerMarket.quick_candidates` defaults to **400 per tag / 600 total**, and `main.py` calls it without explicit limits. Two products stop at 575 and 591, while their categories contain 2,350–5,681 usable rows. This is the first explanation for real alternatives that never appear.
- **France is enforced correctly.** Every returned product was `soldInFrance: true`; `france_unknown` was 0 on the sample, and the final API gate rejects anything not explicitly French.
- **Prices are present but uneven.** 13–207 verified prices per product; some categories are much thinner than others.
- **Gemini is already wired.** `backend/app/webprice.py` does a Google-grounded Gemini lookup, requires a cited page, and is enabled (`GEMINI_API_KEY` is present). The backtest script exists.
- **The UI no longer prefixes prices with “~”.**
- **Existing coverage:** 261 test functions, a 50-barcode `scripts/alt_panel.json`, `scripts/alt_readiness.py`, `scripts/benchmark.py`, `scripts/backtest_webprice.py`.

## What is verified

1. **Retrieval** — candidate pool covers the real category, not just the most scanned slice.
2. **Normalisation** — no valid product lost to parsing, duplicate keys or broken category tags.
3. **France** — every displayed product is confirmed sold in France.
4. **Compatibility** — only genuine substitutes; level 1–2 for strict Valeur/Qualité.
5. **Ranking** — Qualité ignores price; Valeur uses the shared value index; no row worse on both.
6. **Prices** — best available source first, correct unit, date, pack size and citation.
7. **Display** — both tabs, store filter, loading, empty states, French labels, no approximate glyph.
8. **Reliability** — timeouts, quota exhaustion and missing data degrade without inventing an answer.

## Phase 0 — Freeze the baseline

Record commit, OFF dump date, quick-index build time, `value_reference.json` build date, Open Prices date range, webprice cache state, Gemini model, backend env flags and caps.

```bash
cd backend && . .venv/bin/activate
python -m pytest
python -m scripts.alt_readiness http://127.0.0.1:8010 --limit 50
python -m scripts.benchmark --template
python -m scripts.benchmark
python -m scripts.backtest_webprice 200
```

Store p50/p95 latency, fill rate per tab, France pass rate and price coverage. Before trusting `alt_readiness.py`, align its old “sold in France **and at least one chain**” rule with the current contract: France is required, a known chain is optional evidence.

## Phase 1 — Data-source audit

- **OFF local:** total rows, `off_cat` coverage, France-tag coverage, products with no `countries_tags`.
- **Quick index:** build time, row count, missing codes, null grades/nutrients.
- **Open Prices:** French shops only, EUR, date distribution, exact-barcode match rate, per-chain coverage.
- **Gemini/web cache:** provider order, citations, cache hit rate, stale entries, quota pause.

```sql
select tag, count(*) from off_cat where tag in (...) group by tag;
select count(*) from off_cat c join quick.quick q on q.code = c.code where c.tag = ?;
```

## Phase 2 — Candidate recall (core)

Use the 50-code panel and extend it to **100–150 labelled products**, stratified across categories, including store brands and premium products. For each product record:

- the category universe size,
- `diagnostics.raw_candidates_retrieved`,
- `usable_product_data`, `confirmed_sold_in_france`, `france_unknown`,
- `passing_compatibility`, `with_verified_prices`, `by_substitution_level`,
- whether each human-labelled real alternative appears at any stage, and exactly where it is lost: cap, parsing, France, compatibility, price, or ranking cut.

**Baseline action:** raise the 400/600 cap and measure recall vs latency. A full exhaustive pass is only acceptable if parsing thousands of JSON records remains within the latency budget; otherwise the cap must be tuned and documented.

Acceptance:

- known-good recall@10 ≥ 85–90 %;
- no loss caused by an unexplained cap;
- every France rejection explained;
- no loss to parsing or duplicate keys.

## Phase 3 — Ranking correctness

- Qualité: strictly higher nutrition score; price never affects it.
- Valeur: shared `value_index` score; identical score in every tab; UI rows are better in value **or** quality, never both worse.
- No self, no duplicate/variant duplicate, no category-path names.
- Allergens and diet are hard exclusions.
- Deterministic: three identical runs.
- Human labels: “good substitute”, “cheaper”, “better quality”, “good value”.

Acceptance: 100 % invariants; top-5 substitutes ≥ 95 %; incompatible top-5 = 0.

## Phase 4 — Price accuracy and coverage

Source order: receipt → Open Prices exact barcode/date → named chain listing (no price claim) → Gemini web with citation → estimate (never a winner, never unlabelled).

Checks:

- `scripts/backtest_webprice.py 300`: found rate, median error, share within 10/20/30 %.
- Gemini vs Open Prices on the same barcode within 90 days, segmented by category and price band.
- Every web price has at least one source URL; no citation, no price.
- Unit and pack consistency: per 100 g/ml, correct pack size, EUR only.
- Stale prices are downweighted, never silently presented as current.
- No estimate reaches Cheapest or Best value; the UI says when a price is an estimate.
- Coverage: observed vs web vs unpriced, per category.

Acceptance: price correctness ≥ 98 % where a known price exists; 100 % citations; 0 invented; 0 estimates in winners.

## Phase 5 — France compliance

- 100 % of API rows `soldInFrance: true`.
- Open Prices observations located in France and priced in EUR.
- Chains restricted to the French market; no foreign chain leaks.
- Unknown country is not treated as French.

## Phase 6 — End-to-end UI

Matrix: 3 products × 2 tabs × store filter (all / one / none) × Settings chains (empty / two) × price state (observed / web / none).

Verify: better-or-better rule, store filter present on both tabs and persistent, availability line, no Greenweez, no “~”, loading and empty states, 375/390/430 px, no overflow, accessible labels.

## Phase 7 — Reliability and performance

- p50/p95 latency for alternatives and price lookups; 50 concurrent requests.
- Inject Gemini 429/timeout, Open Prices down, missing quick index, stale cache.
- Confirm graceful degradation and no invented prices.
- Verify cache TTLs and that a retry does not duplicate work.

Acceptance: no 500s; documented p95; every failure path returns a truthful empty/partial answer.

## Phase 8 — Sign-off

Report per product and aggregate: pool size vs category, funnel losses, recall, France rate, price coverage and error, tab counts, latency. Gate the release on all acceptance criteria. Save the report in `docs/` and keep the labelled panel under version control.

## Execution log

- Baseline: 6 products, pools 82–591, latency 2.4–4.8 s, France 100 %, 261 test functions.
- Candidate fix: defaults raised to **1,200 per tag / 2,000 total**, configurable with `ALT_PER_TAG` / `ALT_TOTAL`. The same six products now retrieve **1,958 / 478 / 1,027 / 114 / 1,635 / 87** instead of 591 / 171 / 330 / 114 / 575 / 82. Latency is p50 **6.8 s**, p95 **11.2 s** (was 2.4–4.8 s at the 600 cap).
- Price fix: only a diverse **600-item** shortlist is priced (`ALT_PRICE_POOL`), while Qualité still ranks the whole pool. Without this, 2,000 per-barcode price queries took 13–24 s.
- Invariants fixed: one value score per product in every tab; the API now returns only rows better in value **or** quality.
- Readiness: 10 products, **0 violations**, p95 7.8 s; `pytest` **354 passed**; web `tsc`, `vitest` (20/20) and production build clean.
- Gemini: key present and `gemini-3.8-flash` exists, but the live backtest found **0/10** prices because Google answered **429 quota exceeded** / **503 high demand**. `gemini-2.5-flash` is retired for new users and was removed from the fallback list. Re-run `python -m scripts.backtest_webprice 200` when quota resets: price accuracy is not yet certified.
- Open items: 100-product human-labelled recall run; full price backtest; UI matrix.
