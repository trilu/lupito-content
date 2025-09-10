Objective: Run a production pilot on the Top 5 brands to pass quality gates for form, life_stage, ingredients/allergens, and price/price_bucket. Read-additive only; publish to a preview view; no global swap until gates pass.

0) Guardrails
	•	Read-only on prod tables; write to _enrichment / _stg and foods_published_preview (brand-scoped or full preview).
	•	Respect robots.txt; 2–3s delay + jitter; cache HTML/JSON-LD/PDF in GCS with provenance.
	•	Every enriched field: {source_domain, fetched_at, method(html|jsonld|pdf), confidence} + *_from.

1) Pick brands & set profiles
	•	From foods_published, select Top 5 brands by SKU count.
	•	For each, finalize /profiles/brands/<brand>.yaml (list pages/sitemaps, CSS/XPath, JSON-LD: true/false, PDF link patterns, rate limits).

2) Harden the harvester (for these 5)
	•	Enable headless browser for JS sites; add proxy rotation (low volume). Use ScrapingBee API if needed, which is already implemented.
	•	Ensure JSON-LD extraction (Product/Offer), PDF fetching, and pack-size parser (e.g., 12×85g, 2 kg, 3x400 g → kg).
	•	Kcal sanity & Atwater fallback if macros exist; otherwise leave null (no outliers).

3) Enrich & reconcile to preview
	•	Write results to foods_enrichment_manuf (or _v2), then compose foods_published_preview with precedence:
overrides > enrichment_prices_v2 (if any) > enrichment_classify_v2 (if any) > enrichment_manuf > original_source > default.
	•	Indexes on (product_key), (brand_slug), (form), (life_stage), (price_bucket).

4) Brand-level acceptance gates (must pass for each brand)
	•	form ≥ 95% and life_stage ≥ 95% (within that brand)
	•	ingredients_tokens ≥ 85% and allergen_groups ≥ 85%
	•	price_bucket ≥ 70% and for enriched rows: price_per_kg_eur ≥ 50%
	•	0 kcal outliers post-repair; conflicts ≤ 2%

5) Reports (under /reports/MANUF/ + one all-up summary)
	•	MANUF_BRAND_QUALITY_<brand>.md: before→after coverage, sample rows, conflicts.
	•	MANUF_PRICING_<brand>.md: price_per_kg distribution + bucket shares.
	•	MANUF_PILOT_SUMMARY.md: which brands passed gates; per-brand deltas; recommended next 5 brands.

6) Deliver back:
	1.	A one-pager with before→after metrics per brand.
	2.	A 50-row sample CSV per brand (name, form, life_stage, kcal, price_per_kg_eur, price_bucket, allergen_groups, and all *_from).
	3.	Confirmation that foods_published_preview is ready for Admin/AI to test (no global swap yet).