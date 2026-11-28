# Alternatives: plan to make every category credible

Goal: for every one of the 1,000 reference categories (`docs/` audit list, French and English names), a shopper who scans a
product in that category gets alternatives that are the same kind of product, really priced, sold at supermarkets they use, and
genuinely better on value or quality. Fresh unbranded produce (sections 16-17) is out of scope.

## What "credible" means (the bar every category must pass)

A category passes when, for its 5 most-scanned products (not just one):

| # | Criterion | Threshold |
|---|---|---|
| C1 | Alternatives shown | >= 5, unless the product is "already great" |
| C2 | Precision: every shown alternative is the same type, or a declared sibling type | 100 % on the automatic check, >= 95 % on a hand-labelled sample |
| C3 | Chain spread | >= 3 distinct chains in the list; no chain on more than 80 % of rows |
| C4 | Price tiers | at least one store brand and one national brand, when the category has both |
| C5 | Real improvement | at least one alternative cheaper per kg and one with a higher quality score |
| C6 | No duplicates | the same product under another barcode or pack size appears once |

Today's audit only measures C1 (and C3 roughly) on one product per type. That is the first thing to fix, because a count of 10
says nothing about whether the 10 are right.

## Where things stand (2026-11-28, local data)

- French names: 992 / 1,000 placed on a type, 921 with >= 5 alternatives (was 950 / 883 before this session's fixes).
- English names: 847 / 1,000 placed before the English rule pack; 129 of the 153 gaps now classify.
- Chains: 413 of 633 category lists draw on >= 8 chains; 13 rely on 1-2 chains (lamb cuts, gorgonzola, gambas, coleslaw).
- Products: 82.1 % of the 1.12 M local products sit on a specific type; 15.4 % are unclassified.
- The quality floor is gone; only a missing score excludes a candidate.

## Phases

### Phase 1 - Measure properly (precision audit)
1. Audit 5 products per type instead of 1, chosen by scans across different brands.
2. Precision check for every shown alternative: re-classify its name and flag it when its type is neither the scanned type nor a
   declared sibling; flag dish words (sauce, plat, salade...) and ingredient-only matches.
3. Record C1-C6 per category in one CSV and a summary table; keep each run, so regressions show.
4. Hand-label a 300-row sample (`scripts.make_taxonomy_sheet` / `score_taxonomy_sheet`) to calibrate the automatic check.

Gate: the audit reports C1-C6 for all in-scope categories.

### Phase 2 - Fix placement (the taxonomy)
1. Work the precision failures from phase 1, worst categories first; every fix gets a golden case
   (`tests/data/taxonomy_golden.json`).
2. Merge split families: the same food living in two categories (the blue cheeses did), so the category gate never sees its peers.
3. Declare sibling types (sliced / plain smoked salmon; lamb chop / lamb shoulder; UHT / fresh milk) and use them as the middle
   tier of the gate: exact type -> siblings -> category. Today only a product's own secondary types act as siblings.
4. Cut the 15.4 % unclassified share, starting with the products that are most scanned and best priced.

Gate: automatic precision 100 % on the audit, >= 95 % on the hand sample.

### Phase 3 - Fill thin pools
1. For each category failing C1 or C3, find whether the cause is no products, no prices or no chain evidence.
2. Prices: more Open Prices coverage and receipts; never an estimate shown as a price.
3. Chain evidence: store-brand mapping (`chains.py`) for every chain's own brands; brand-to-chain data where it is real.

Gate: C1 and C3 pass for >= 95 % of categories; each remaining failure has a named data reason.

### Phase 4 - Rank for a useful list
1. Diversity: at most 2 rows per brand, and spread across chains when the pool allows (C3).
2. Tiers: make sure a store brand and a national brand both appear (C4).
3. Each list carries a cheapest-per-kg pick and a best-quality pick (C5); duplicates folded (C6).
4. Decide the "already great" case: show cheaper equivalents with the note, instead of an empty screen.

Gate: C1-C6 pass for >= 95 % of categories.

### Phase 5 - Keep it true
1. A CI test runs the audit on a frozen 100-category fixture and fails on any regression in C1-C6.
2. The full 1,000-category audit runs after every taxonomy change and every data import.
3. Production: run `scripts/build_taxonomy_index` on the production and US copies after each rule change (back up
   `off_taxo` / `off_tax` first), then re-audit there.

## Decisions recorded

- No quality floor: categories capped by salt or sugar (smoked salmon, saucisson, white chocolate) were emptied by a fixed floor
  of 50. Within one type, the ranking and the "better than yours" rules decide; an unknown score still excludes.
- Gate tiers: exact type, then the product's own other types, then the category. A whole category is the last resort because it
  mixes forms (sardines next to smoked salmon).
- Smoked salmon pieces (brisures, dés, émincés, cœur) are their own type, so a sliced pack is compared with slices.
- Frozen vegetables and fruit sit in the frozen category, because an ingredient-category type is refused when the name carries a
  form word such as "surgelé".
- Re-placing products after a rule change: use `scripts.build_taxonomy_index` (parallel, ~35 min) with a table backup.
  `scripts.reclassify_subset` is for a handful of rare keywords only; common words make it rescan the whole table per keyword.
