Objective: Replace OPFF with a Manufacturer-first enrichment. Harvest label facts (ingredients/macros/kcal/life-stage/form) and, where available, pricing signals via JSON-LD. Respect robots.txt. Work read-additive, publish via foods_published_v2, and only swap after gates pass.

⸻

0) Guardrails
	•	Read-only on production tables. All writes go to _enrichment / _stg tables and foods_published_v2.
	•	Respect robots.txt and low rate limits (≥2s delay + jitter). Cache all HTML/PDF/JSON in GCS with provenance.
	•	Field-level provenance required: {source_domain, fetched_at, method(html|jsonld|pdf), confidence} and *_from ∈ {override,enrichment,source,default}.

⸻

1) Brand prioritization
	•	Generate /reports/MANUF_BRAND_PRIORITY.md and CSV from foods_published: Top 30 brands by product count and Top 500 SKUs.
	•	For each brand, create a row with: brand site URL, sitemap/product-list URLs if known, robots status, presence of JSON-LD Product, presence of spec/PDF links.

⸻

2) Source profiles (per brand)
	•	Create /profiles/brands/<brand_slug>.yaml containing:
	•	list_pages (category URLs), pdp_selectors (CSS/XPath for: product_name, composition/ingredients, analytical constituents, life-stage text, form hints, pack size), jsonld=true|false, pdf_selectors (anchor patterns like “spec”, “composition”, “analytical”), and rate limits.
	•	Start with 10 brands that look easiest (JSON-LD present or clear PDP blocks).

⸻

3) Harvest jobs
	•	Build jobs/brand_harvest.py that reads a brand profile and:
	1.	Collects PDP URLs (from sitemap/list pages).
	2.	Saves raw HTML and JSON-LD (if present) to GCS.
	3.	Follows PDF links (up to 2 per PDP) → store PDF file.
	4.	Emits a per-run report (new/updated/skipped/failed).

⸻

4) Parsers (HTML / JSON-LD / PDF)
	•	HTML parser: extract ingredients_text, composition lines, analytical constituents (%), life-stage phrases, form hints, pack size.
	•	JSON-LD parser: schema.org Product/Offer → brand, name, description, offers.price, priceCurrency, maybe weight.
	•	PDF parser: detect text; parse “Composition / Analytical constituents / Additives” tables; extract kcal if present.
	•	Normalize into foods_enrichment_manuf with:
	•	ingredients_tokens, allergen_groups (use our existing mapping), ingredients_unknown=false when tokens present
	•	protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent
	•	kcal_per_100g (or kcal_from="estimate" via Atwater if macros suffice)
	•	form (dry|wet|freeze_dried|raw), life_stage (puppy|adult|senior|all)
	•	price_eur, price_per_kg_eur (from JSON-LD Offer + parsed pack size)
	•	provenance + confidence

⸻

5) Reconcile (v2) & indexes
	•	Update foods_published_v2 precedence:
overrides > enrichment_prices_v2 (if exists) > enrichment_classify_v2 (if exists) > **enrichment_manuf** > original_source > default.
	•	Ensure ingredients_unknown is strictly boolean.
	•	Indexes on (product_key), (brand_slug), (form), (life_stage), (price_bucket).

⸻

6) Quality gates (must pass to swap)
	•	form ≥ 95%, life_stage ≥ 95% (catalog-wide)
	•	ingredients_tokens ≥ 85% and allergen_groups ≥ 85%
	•	price_bucket ≥ 70%, with price_per_kg_eur ≥ 50% for enriched rows
	•	0 kcal outliers after sanity checks
	•	Conflicts ≤ 2% (via *_from comparison)

⸻

7) Reports (put under /reports/MANUF/)
	•	MANUF_BRAND_PRIORITY.md (brand list, robots, JSON-LD/PDF presence)
	•	MANUF_HARVEST_SUMMARY.md per brand (counts, error reasons)
	•	MANUF_FIELD_COVERAGE_BEFORE.md vs MANUF_FIELD_COVERAGE_AFTER.md (form/life_stage/ingredients/kcal/price)
	•	MANUF_PRICING_COVERAGE.md (per-kg distribution, bucket shares)
	•	MANUF_CONFLICTS_SAMPLE.csv (100 rows where manuf data differs; show which source wins)
	•	MANUF_SAMPLE_100.csv (product_name, form, life_stage, kcal, price_per_kg_eur, price_bucket, allergen_groups, and all *_from)

⸻

8) Swap & maintain
	•	If all gates pass, atomically point foods_published → v2; keep _prev for rollback.
	•	Schedule weekly light refresh for the 10 brands and rotate the next 10.

⸻

Optional (helps a lot)
	•	Add a tiny “Data Fixer” in Admin for the top 200 SKUs: paste ingredients string / upload label PDF, then the pipeline parses & writes to foods_overrides. This lets you close stubborn gaps fast while the harvest scales.