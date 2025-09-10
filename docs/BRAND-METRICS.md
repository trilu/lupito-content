Task: Add a brand metrics view so Admin can query fast.

1) Create two SQL views (or materialized views):
	•	foods_brand_quality_preview (built from foods_published_preview)
	•	foods_brand_quality_prod (built from foods_published_prod)

2) Each view should expose (one row per brand_slug):
	•	brand_slug, sku_count
	•	form_cov, life_stage_cov, ingredients_cov, kcal_cov, price_cov, price_bucket_cov
	•	completion_pct = average of the five coverages (form, life_stage, ingredients, kcal, price)
	•	kcal_outliers (count)
	•	status (PASS/NEAR/TODO per thresholds below)
	•	last_refreshed_at

3) Status thresholds (match Admin):
	•	PASS if form_cov>=0.95 and life_stage_cov>=0.95 and ingredients_cov>=0.85 and price_bucket_cov>=0.70 and kcal_outliers=0
	•	NEAR if within 5pp on any PASS threshold
	•	TODO otherwise

4) Index & refresh
	•	If materialized, refresh nightly + on demand.
	•	Index on (brand_slug) and (sku_count desc) for fast lists.

5) Deliverables
	•	/sql/foods_brand_quality_views.sql
	•	/reports/FOODS_BRAND_SCOREBOARD.md with Top 20 brands by SKU and their completion %, highlighting PASS/NEAR/TODO.