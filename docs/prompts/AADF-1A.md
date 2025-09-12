Fix staging + dry-run matching (no writes)

Goal: Create a staging table that actually matches the AADF CSV, load it, and tell us exactly how many rows will safely enrich the existing catalog—without changing any production tables yet.

	•	Inspect data/aadf/aadf-dataset.csv headers and compare to any existing retailer_staging_aadf* table.
	•	Create/replace a new staging table (name it retailer_staging_aadf_v2) with columns that align to the CSV and our normalization:
	•	brand_raw, brand_slug
	•	product_name_raw, product_name_norm
	•	url, image_url
	•	form_guess, life_stage_guess
	•	ingredients_raw, ingredients_language
	•	kcal_per_100g, protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent
	•	pack_sizes, gtin (if available)
	•	source (constant 'aadf'), ingested_at (timestamp), row_hash (content hash), product_key_candidate
	•	Load all 1,101 rows into retailer_staging_aadf_v2.
	•	Normalize:
	•	brand_slug via existing brand map.
	•	product_name_norm (strip size/flavor/skus; lowercase; collapse spaces).
	•	Detect ingredients_language.
	•	Dry-run matching (no writes): compute similarity between (brand_slug, product_name_norm) and foods_canonical:
	•	High: ≥0.80, Review: 0.65–0.79, No-match: <0.65.
	•	Report per-brand counts and overall histogram.
	•	Output:
	•	reports/AADF_STAGE_AUDIT.md (updated with staging load + normalization stats).
	•	reports/AADF_MATCH_FEASIBILITY.md (high/review/no-match totals; top brands by high matches; sample rows).
	•	Do not modify foods_canonical / views. Stop after reports.