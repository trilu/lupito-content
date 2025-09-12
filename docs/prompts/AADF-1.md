AADF: Stage & Audit (no writes to canonical)

Goal: Load data/aadf/aadf-dataset.csv into a staging table, extract clean brand/product names, and produce an audit so we know exactly what we have—without changing production.

Run as-is, no code pasted back.
	1.	Confirm the retailer staging SQL objects exist (create if missing): a dedicated table like retailer_staging_aadf with columns for raw_url, brand_guess, product_guess, form_guess, life_stage_guess, ingredients_raw, kcal_per_100g, pack_sizes, source='aadf', ingested_at.
	2.	Load data/aadf/aadf-dataset.csv into retailer_staging_aadf.
	3.	Derive brand and product names for each row using this order:
	•	(a) Parse from URL path segments (brand in first segment; product in second; strip hyphens, numbers, pack sizes, and flavor tails).
	•	(b) If URL ambiguous, fetch page title/H1 once and extract brand/product from on-page labels.
	•	(c) Normalize brand via our existing brand map; set brand_slug.
	•	(d) Normalize product name: remove size/weight/flavor suffixes, collapse whitespace, lowercase → product_name_norm.
	4.	Classify form and life_stage from tokens (dry/wet/freeze_dried/raw; puppy/adult/senior) using our existing rules; store as form_guess/life_stage_guess.
	5.	Produce AADF AUDIT (Markdown):
	•	Row count, distinct brands, top 20 brands by rows.
	•	Coverage: % with brand_slug, % with product_name_norm, % with form_guess, % with life_stage_guess, % with ingredients_raw.
	•	Sample 20 ambiguous rows that still lack brand/product after derivation.
	•	“Treats/toppers” estimate (flag candidates to exclude from complete foods).
	6.	Do not write to foods_canonical yet. Report only:
	•	File: reports/AADF_STAGE_AUDIT.md
	•	Counts by brand and an “OK to proceed” boolean if brand/product extraction ≥90% and form/life_stage ≥80%.