Objective: Produce a clear, decision-ready baseline of our pet food catalog quality and gaps. Focus on foods_published (current source for AI/Admin), and compare to other tables (food_candidates, food_candidates_sc, food_brands, foods_enrichment, foods_overrides, food_raw if present). No code in this message; you generate the SQL/scripts/reports.

⸻

0) Guardrails
	•	Do not modify production data. Read-only audit.
	•	Save all outputs under /reports/ and any helper SQL under /sql/audit/.
	•	Every number in the summary must be reproducible by a saved query.

⸻

1) Inventory & Row Counts
	•	Report total rows for each table/view:
foods_published, food_candidates, food_candidates_sc, food_brands, foods_enrichment, foods_overrides, food_raw (if exist).
	•	In foods_published, confirm product_key uniqueness. If duplicates: count and top examples (brand, product_name, form, pack size if any).

Output: FOODS_AUDIT_BASELINE.md (section: Inventory & Uniqueness), plus duplicates_product_key.csv if any.

⸻

2) Field Coverage (the big picture)

On foods_published, compute % coverage for key fields:
	•	Composition/ingr.: ingredients_tokens, ingredients_unknown (boolean rate true/false)
	•	Nutrition: kcal_per_100g, macros (protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent)
	•	Classification: life_stage (puppy|adult|senior|all), form (dry|wet|freeze_dried|raw)
	•	Pricing: price_eur, price_per_kg_eur, price_bucket (low|mid|high)
	•	Availability: available_countries (if present)
	•	Provenance: per-field *_from flags (override|enrichment|source|default) and fetched_at/updated_at

Also produce a null matrix (field vs % missing).

Outputs:
	•	FOODS_FIELD_COVERAGE.csv (field, coverage_pct)
	•	FOODS_NULL_MATRIX.csv (field, missing_pct)
	•	Summary in FOODS_AUDIT_BASELINE.md (Coverage & Nulls).

⸻

3) Quality Distributions & Outliers
	•	Kcal distribution (by form): median, p10, p90; flag outliers (e.g., dry < 250 or > 500 kcal/100g; wet < 40 or > 150).
	•	Macro sanity: protein/fat plausible ranges by form (flag absurd values).
	•	Life-stage naming consistency: compare life_stage vs product_name tokens (“puppy”, “kitten/senior/adult”). Count mismatches.

Outputs:
	•	FOODS_KCAL_DISTRIBUTION.csv (form, median, p10, p90)
	•	FOODS_KCAL_OUTLIERS.csv (product_key, form, kcal, reason)
	•	FOODS_LIFESTAGE_MISMATCH.csv
	•	Narrative summary in FOODS_AUDIT_BASELINE.md (Distributions & Outliers).

⸻

4) Ingredients Tokens Reality Check
	•	Coverage of ingredients_tokens overall and by brand (top 50 brands by product count).
	•	Top 30 most common proteins/cereals tokens.
	•	Allergy readiness: % of products where we can reliably detect chicken, beef, salmon/fish, grain/gluten.
	•	“Unknown ingredients” rate by brand (helps target enrichment).

Outputs:
	•	FOODS_INGREDIENTS_COVERAGE_BY_BRAND.csv (brand, products, tokens_coverage_pct, unknown_rate)
	•	FOODS_TOP_TOKENS.csv (token, count)
	•	FOODS_ALLERGY_SIGNAL_COVERAGE.csv (token_group, coverage_pct)
	•	Summary & prioritized brand list in FOODS_AUDIT_BASELINE.md (Ingredients & Allergy Readiness).

⸻

5) Pricing Reality Check
	•	Coverage of price_bucket and price_per_kg_eur overall and by brand.
	•	Median price_per_kg_eur by brand & form for brands with ≥10 products.
	•	Count products with price but no bucket.
	•	Simple bucket thresholds used (if defined) — document them; if not defined, propose thresholds based on distribution.

Outputs:
	•	FOODS_PRICE_COVERAGE.csv (overall, by brand)
	•	FOODS_PRICE_PER_KG_BY_BRAND_FORM.csv
	•	Narrative in FOODS_AUDIT_BASELINE.md (Pricing Coverage & Buckets).

⸻

6) Availability & Freshness
	•	If available_countries exists: % with EU availability; breakdown by country (top 10).
	•	Freshness: distribution of fetched_at/updated_at; % older than 180 days.
	•	Provenance: share of values coming from override / enrichment / source / default (per field).

Outputs:
	•	FOODS_AVAILABILITY_COUNTRIES.csv
	•	FOODS_FRESHNESS.csv (age buckets)
	•	FOODS_PROVENANCE_SHARE.csv (field, override%, enrichment%, source%, default%)
	•	Summary in FOODS_AUDIT_BASELINE.md (Availability & Freshness).

⸻

7) Brand Leaderboard (where to focus first)

For top 50 brands (by product count in foods_published):
	•	ingredients_tokens coverage %
	•	kcal_per_100g coverage %
	•	life_stage/form coverage %
	•	price_bucket coverage %
	•	Quality score (weighted): tokens 40%, kcal 25%, life_stage+form 25%, price_bucket 10%.
Sort descending by product count, and show the bottom 15 by score as our enrichment priority.

Output: FOODS_BRAND_QUALITY_LEADERBOARD.csv + a ranked table in FOODS_AUDIT_BASELINE.md.

⸻

8) Source Comparison (sanity)

Where the same product_key exists in multiple source tables (candidates, brands, etc.), sample 100 overlaps and report field conflicts (kcal, life_stage, form).
Show which source wins in foods_published (via *_from).

Outputs:
	•	FOODS_SOURCE_CONFLICTS_SAMPLE.csv
	•	Notes in FOODS_AUDIT_BASELINE.md (Cross-Source Consistency).

⸻

9) Index & Performance Check
	•	Confirm indexes on foods_published(product_key), (brand_slug), (form), (life_stage).
	•	Record median latency of 3 representative queries (by brand, by form+life_stage, by product_key).

Output: FOODS_INDEX_CHECK.md (what exists, suggestions if missing).

⸻

10) Executive Summary & Next Actions

In FOODS_AUDIT_BASELINE.md (top of file), include:
	•	One-page Executive Summary with 5–7 bullets: overall coverage, biggest gaps, any outliers.
	•	Top 5 brands to enrich next (impact vs effort).
	•	Top 5 fields to enrich globally (e.g., ingredients tokens, price_bucket) with suggested approach (JSON-LD, PDFs, heuristics).
	•	A Prioritized 10-item backlog with clear, bite-sized tasks (each with expected coverage lift).

⸻

Deliverables Recap
	•	/reports/FOODS_AUDIT_BASELINE.md (the main doc, with embedded tables where helpful)
	•	/reports/*.csv files listed above
	•	/sql/audit/*.sql with the exact queries used

Please run the full analysis and paste back:
	1.	The Executive Summary section,
	2.	The Brand Quality Leaderboard (top & bottom 10),
	3.	A short list of the Top 10 SKUs we should enrich first (by impact), with the missing fields called out.