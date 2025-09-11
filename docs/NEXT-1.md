Pick the next 3 brands + plan the harvest

Goal: choose the next three high-impact brands and produce a concrete, low-risk harvest plan.

Do:
	1.	Recompute the impact queue from live Supabase (Preview scope). Prioritize brands with:
	•	highest SKU count × (100 – ingredients coverage),
	•	manufacturer site publicly reachable (no hard block),
	•	likely English or well-structured sites.
	2.	Select the top 3 (“Wave-Next-3”). For each, confirm:
	•	official manufacturer domain(s) + canonical product listing/category URLs,
	•	robots.txt stance (ok/caution/block),
	•	expected content locations (HTML, PDF, JSON-LD),
	•	page count estimate and throttling plan.
	3.	Prepare WAVE_NEXT_PLAN.md with:
	•	the 3 chosen brands and why they were picked,
	•	exact seed URLs (categories/sitemaps) and any auth/headers needed,
	•	parsing focus for ingredients + macros (price out of scope),
	•	acceptance gates for each brand (Preview):
	•	ingredients_tokens ≥ 85% of SKUs (non-empty),
	•	kcal_per_100g in 200–600 for ≥ 90%,
	•	form+life_stage classified for ≥ 90% (via existing rules),
	•	0 kcal outliers in target range.
	4.	Do not touch Prod allowlist. This is planning only.

Deliver:
	•	WAVE_NEXT_PLAN.md (concise 1–2 pages) and a one-paragraph summary in the chat with the three brand names.