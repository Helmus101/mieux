# Mieux: business plan

Written for the founder, shareable with partners or advisers. Figures marked **[source]** come from a link in the Sources section. Figures marked **[assumption]** are my working guesses and must be validated before they are used to decide anything.

## 1. Summary

Mieux is a free, mobile-first web app (PWA) for France. A shopper scans a food product and gets (1) a nutrition and additive score out of 100, then (2) three alternatives: the cheapest, the best quality, and the best quality-for-price. Existing apps do one half: health scanners (Yuka) do not compare prices, and price scanners (Prixing, retailer comparators) say nothing about quality.

The opportunity is real but narrow. The single biggest risk is price data: the cheapest and best-value picks are only as good as the community prices behind them. The business should therefore be built around getting price coverage, not around the score.

Honest outlook: as a consumer subscription app, Mieux is a small business unless it reaches Yuka-like scale (section 9). Treat the first six months as a product-validation period, not a revenue plan.

## 2. The problem

- Health scanners tell you a product is bad but not what to buy instead at a price you accept. Their alternatives are not price-based.
- Price scanners compare stores for the same product but ignore whether a cheaper product is worse for you.
- Shoppers who care about both (a family, a student, anyone watching the grocery bill) must use two apps and combine the answers in their head, in the aisle.
- Food-price pressure has pushed French shoppers to trade off more: a 2022-23 survey of 1,011 people found 40% use price or review comparison apps, 18% since inflation began **[GetApp survey, not food-specific, dated]**. National brands rose faster than private labels in March 2024 (+3.4% vs +2.7%) **[NielsenIQ]**, which is exactly the trade-off Mieux makes visible.

## 3. The solution and what makes it different

One scan, one screen:

1. Score out of 100: 40% nutrition (calories at half weight), 25% additives, 25% ingredient quality (added sugar, artificial additives, ultra-processing), 10% organic. Yuka publishes a 60/30/10 split of nutrition, additives and organic **[source]**; Mieux deliberately weighs ingredient quality more.
2. Three alternatives in the same category: cheapest (per 100 g), best quality, best value, each with the price and score difference.
3. Every additive explained: what it does, where it is usually found, health note and source.
4. Privacy by design: scans, preferences and history stay on the phone; the account stores only a scan count.

Unique value proposition (one sentence): *"Yuka tells you it's bad. Mieux tells you what to buy instead, and what you save."*

Defensibility is weak today (the score logic is public knowledge, the data is open). What can become defensible: price coverage and freshness, a trusted brand for honest scoring, and the shopper's own history (savings tracked over time).

## 4. Target market

### 4.1 Primary segment: budget-aware, health-aware shoppers (25-45)

- Households managing a weekly grocery budget who already read labels or have used a scanner.
- Why first: they feel both pains and the savings are concrete (euros per basket).
- Where they are: Instagram and TikTok (budget, "courses", meal-prep, anti-waste content), Reddit and Facebook groups on saving money, parent communities.
- What they need to see in the first minute: a real product from their own kitchen, with a cheaper and a better alternative.

### 4.2 Secondary segment: students and young adults (18-25)

- Tight budgets, high willingness to try free apps, strong word of mouth, low willingness to pay.
- Good for volume and for price contributions, poor for revenue.

### 4.3 Secondary segment: health-first shoppers (parents of young children, people managing a condition)

- Motivated by additives and sugar; price matters less. Mieux's additive explanations and allergen exclusions serve them, but Yuka already owns this need, so Mieux should not lead here.

### 4.4 Not targeted at launch

Cosmetics buyers (Yuka covers it), people shopping mainly online or by delivery, and anyone outside France (product and price data are France-first).

### 4.5 Market size

I do not have sourced figures for the number of French grocery-app users, so I do not state a TAM. A defensible way to size it once validated:

- Reachable users = smartphone owners who shop for groceries and have a reason to compare (survey: 40% use comparison apps **[GetApp, dated]**).
- Benchmark for the ceiling: Yuka reports about 85 million users across 12 countries (BBC, July 2026) **[source]**, which shows the behaviour (scanning) is mainstream. Mieux will not reach that scale soon.
- Practical planning targets **[assumption]**: 1,000 active users in 3 months, 10,000 in 12 months. These are goals to test, not forecasts.

## 5. Competition

| | Health score | Price comparison | Alternatives | Notes |
|---|---|---|---|---|
| Yuka | Yes, very large user base | No | Healthier, not price-based | Free plus premium (€10/year); says it takes no ads or sponsored rankings **[source]** |
| Open Food Facts | Database and Nutri-Score | Open Prices, community | Browse, not curated | Mieux builds on its data (ODbL) |
| Vutro (new) | Yes | Cheaper alternative claimed | Yes | Described in one 2026 article; **not verified**. The closest competitor to check first **[source]** |
| Prixing, TousLesPrix | No | Yes, by store | No | Older apps, activity today unknown |
| Retailer comparators (Leclerc, Auchan) | No | Own stores only | No | Locked to one chain |

Mieux's gap in the market is real only if it can show prices more often and more accurately than competitors, and can keep health quality in the same view. Check Vutro before spending money on marketing.

## 6. Product and roadmap

Today: scan, score, three alternatives, additive detail, allergen and diet exclusions, per-account local data, install-to-home-screen, blog, landing page.

Priorities, in this order:

1. **Price coverage (the make-or-break item).** Let users contribute a price in two taps after a scan; receipt scanning; show "last seen, where, how long ago"; contribute to Open Prices so the data improves for everyone. Measure the share of scans that return a dated real price, separate from estimates.
2. **Retention loop.** A weekly "you could have saved €X" summary from the user's own scans. Without it, scanning is one-off.
3. **Distribution.** Wrap the PWA for the Google Play and App Store (iPhone Safari limits: camera permission on every load, manual install steps). This is likely worth doing once there are a few thousand users.
4. **Quality assurance.** A public "why this score" page, an in-app "report a problem" flow, and monitoring of the products most often scanned.
5. Later: shopping list, store-by-store basket totals, English UI polish.

## 7. Go-to-market

Phase 1 (weeks 1-4): 50 people, learn.
- Personal network, plus 3-5 micro-creators in budget or healthy-eating niches.
- Success measures: share of users who scan at least 3 products in week one; share who open an alternative; share who return in week two; every complaint about a wrong score or missing price logged.

Phase 2 (months 2-4): reach 1,000 active users.
- Short vertical videos built on one idea: *a bad score, then the alternative and what it saves.* One real product per video, filmed in a supermarket aisle.
- Instagram and TikTok are the main channel; reuse the existing post and reel assets.
- SEO: the blog (additive explainers, "Yuka ou Mieux" comparison) targets searches such as "additif E471", "alternative à Yuka".
- Student associations and parent groups; a "30-day grocery challenge" that gives people a reason to scan daily.
- Press angle for consumer media: independent, privacy-first, built on open data.

Phase 3 (months 5-12): 10,000 users, monetisation test.
- Introduce premium once there is a clear feature people ask for (history, savings reports, offline).

Metrics that matter: activation (first scan within 24 h), alternatives tapped per scan, 7-day and 30-day retention, share of scans with a real price, average euros saved per active user, cost per active user.

## 8. Revenue model

Principle: stay independent. No sponsored rankings, no retailer-paid placement. That independence is the brand, and it is what Yuka sells too **[source]**.

Options, in order of preference:

1. **Premium subscription** (Yuka's model works: its 2023 published breakdown shows €3.5M from premium, €0.23M from books and calendars, €0.07M from services **[source]**). Price anchor: Yuka charges €10/year. A Mieux premium at a similar price **[assumption]** could include savings history, shared household lists, offline mode.
2. **Affiliate or retailer link-outs**, only if transparent and never affecting rankings. Risky for trust; avoid until the product is established.
3. **Aggregated, anonymous insights** for brands or researchers. Needs care with privacy and trust; not before a large user base.

## 9. Financial scenarios (illustrative)

These are arithmetic on assumptions, not forecasts. Premium price €10/year **[assumption]**, conversion as shown **[assumption]**.

| Scenario | Active users | Paying share | Yearly revenue |
|---|---|---|---|
| Slow | 5,000 | 1% | about €500 |
| Base | 20,000 | 2% | about €4,000 |
| Strong | 50,000 | 3% | about €15,000 |

Costs in year one **[assumption]**: hosting (Fly.io, Vercel, Supabase) and a domain, likely in the low thousands of euros at most at this scale; check current plan pricing. Legal basics (privacy policy, trademark search) add a one-off cost. Marketing is mostly time, not money.

Reading: at consumer-subscription scale this does not pay a salary until tens of thousands of paying users. Yuka reaches its scale through tens of millions of users, so the conversion rate can be tiny **[source]**. Mieux needs either that scale or a second revenue line. Decide after the 12-month validation, not before.

## 10. Operations

- Stack: React web app (PWA) on Vercel; FastAPI backend with SQLite on a single Fly.io machine; Supabase for sign-in only; Open Food Facts and Open Prices data under the ODbL licence.
- Single point of failure: one backend machine. A second machine adds cost and some complexity; consider it once usage is steady.
- Team: one founder. Time budget is the real constraint; focus on price coverage and retention.

## 11. Legal and compliance (check with a professional)

- **Open data licences:** Open Food Facts and Open Prices are ODbL: attribute them (the app does in the footer) and respect share-alike for derived databases.
- **Privacy (GDPR):** accounts hold an email address and a scan count. Publish a privacy policy, state where data is stored (Supabase region), and provide account deletion (exists in the app).
- **Health claims:** present the score as information, not medical advice. A visible disclaimer is advisable.
- **Comparative advertising:** in France, comparing with a named competitor is allowed only if the claims are truthful, verifiable and not misleading. The blog and landing page compare on checkable facts (price, alternatives, cosmetics coverage) and avoid judgement words about Yuka.
- **Trademark:** search INPI and EUIPO for "Mieux" in classes for software and food information before investing in the brand.
- **Reused code:** the app copies no third-party code beyond libraries; keep licence notices.

## 12. Risks and what to do about them

| Risk | Likelihood | Impact | Action |
|---|---|---|---|
| Price data too sparse; "cheapest" is often missing or stale | High | High | Make price contribution a core feature; show data freshness; be explicit when a price is an estimate |
| Open Food Facts errors produce odd scores | Medium | Medium | "Report a problem" flow; "why this score" page; fix the top-scanned products first |
| A competitor (Vutro, or Yuka adding prices) does the same | Medium | High | Verify Vutro now; move faster on price coverage and savings history |
| Users scan once and never return | High | High | Weekly savings recap; shopping list; test retention in phase 1 |
| Low premium conversion | High | Medium | Keep costs low; test a second revenue line after validation |
| iPhone PWA friction (install steps, camera prompts) | Medium | Medium | Store wrappers once a few thousand users |
| Legal challenge over comparisons or health claims | Low | High | Keep claims factual and sourced; disclaimers; professional review before scaling ads |
| Single founder, single server | High | Medium | Monitoring, backups, a second machine when usage justifies it |

## 13. Next 90 days

1. Verify the live deployment on real phones; scan 20 products from your own kitchen and log every wrong or missing result.
2. Check Vutro in detail (features, pricing, user base) and write a one-page comparison.
3. Run the 50-person pilot; interview 10 of them for 15 minutes each (what did you scan, what did you buy, would you pay).
4. Build the price-contribution flow and measure the share of scans with a real dated price.
5. Publish the privacy policy and run the trademark search.
6. Publish 12 short videos on one repeatable format; track which hook gets saves and shares.
7. At day 90, decide: keep going (retention above your threshold), pivot to the strongest segment, or stop.

Suggested thresholds **[assumption]**: at least 25% of new users return in week two, at least 60% of scans return a real or clearly marked estimated price, and at least 10 people say they would pay.

## 14. Open questions to answer with real users

- What do people do right after seeing an alternative: buy it, remember it, ignore it?
- Is price or quality the stronger reason to open the app?
- Do they trust a score from an app they have not heard of, and what would build that trust?
- What would they pay for, and how much?

## Sources

- Yuka user numbers: BBC report of July 2026, republished by [The Star](https://www.the-star.co.ke/news/world/2026-07-15-is-tracking-your-food-purchases-good-for-your-health).
- Yuka financing, no-ads statement and premium: [Yuka help centre, financing](https://help.yuka.io/l/en/article/zrgtb8f2ka-yuka-financing).
- Yuka's effect and critique of its alternatives: [FoodNavigator, 2019](https://www.foodnavigator.com/Article/2019/08/20/Evaluating-the-Yuka-phenomenon-How-effective-is-the-scanning-app-in-practice/).
- Vutro (unverified): [ladn.eu on food and cosmetics scanner apps](https://www.ladn.eu/tech-a-suivre/applications-scanner-nourriture-cosmetiques/).
- Open Prices volume (global, no France-specific figure found): [Open Food Facts blog, 50k prices](https://blog.openfoodfacts.org/en/news/50k-prices-on-open-prices) and [NLnet project page](https://nlnet.nl/project/OpenPrices/).
- Price-comparison app usage: [GetApp survey](https://www.getapp.fr/blog/3693/utilisation-applications-pour-faire-des-economies); price trends: [NielsenIQ, 2024](https://nielseniq.com/global/fr/insights/analysis/2024/inflations-des-prix-en-france-2/).
- Retailer comparators: [LSA on Leclerc](https://www.lsa-conso.fr/e-leclerc-lance-son-comparateur-mobile,122744) and [on Auchan](https://www.lsa-conso.fr/nouvelles-technologies-auchan-teste-un-comparateur-de-prix-sur-mobile,127304).
- Older price apps: [Prixing](https://www.prodigemobile.com/application-android/prixing-comparateur-prix-android/), [TousLesPrix](https://iphonesoft.fr/2010/09/24/touslesprix-application-du-comparateur-de-prix-en-ligne).
