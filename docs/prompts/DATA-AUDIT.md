RETAILER-DATA AUDIT & STAGING (Chewy + AADF)

Goal: Ingest two local datasets — data/chewy/chewy-dataset.json and data/aadf/aadf-dataset.csv — into a staging workflow, analyze field quality, map to our canonical schema, and produce a “go/no-go” report. Do not write to foods_canonical or published views. Only create local CSVs and (optionally) a retailer_staging_* schema/tables for review.

A) Grounding & Constraints
	•	Use local files only:
	•	Chewy JSON: data/chewy/chewy-dataset.json
	•	AADF CSV: data/aadf/aadf-dataset.csv (note: product name may need to be derived from the link path)
	•	No cloud secrets, no external scraping. No writes to production tables.
	•	Prefer manufacturer data for nutrition; treat retailer data as augment/confirm only.
	•	Respect existing brand normalization assets if present:
	•	data/brand_phrase_map.csv and/or data/canonical_brand_map.yaml
	•	Assume dog products only; exclude obvious toppers/treats if they are not full meals when computing “food coverage” metrics (still report them separately).

B) Minimal Schema Mapping (per source)

Produce a mapping doc for each dataset (Chewy, AADF) showing how fields map into our canonical columns. Include notes for missing/derived values.
	•	Target canonical columns:
brand, brand_slug, brand_family, product_name, name_slug, form, life_stage, kcal_per_100g, protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent, ingredients_raw, ingredients_tokens (json array), price_per_kg_eur, price_bucket, available_countries (json array), sources (json array), product_key
	•	Chewy hints (validate against sample):
	•	url, name, offers.price, offers.priceCurrency, brand.(often “slogan” carries brand), description (contains “Specifications” block with fields like Item Number, Lifestage, Food Form, Special Diet).
	•	Extract form and life_stage from “Specifications”; if absent, infer from name/description.
	•	Extract pack weight from name or description to compute price_per_kg_eur (convert USD→EUR with a static placeholder rate in the report; do not persist currency conversions).
	•	Ingredients: if not explicitly present, leave ingredients_raw empty; do not hallucinate. Use Special Diet as tags only (not ingredients).
	•	AADF hints:
	•	Product name may need to be parsed from the URL path or a slug field in the CSV.
	•	Expect columns for brand, link, and review text; derive form/life_stage from link/title tokens if reliable; treat any reviewer “ingredients” text as non-authoritative.

C) Normalization & Keys
	•	Normalize brand using our maps; generate brand_slug and brand_family.
	•	Build name_slug from product_name (lowercase, hyphenated, [a-z0-9-] only).
	•	Derive deterministic product_key = brand_slug + "::" + name_slug (optionally append form or primary protein if needed to avoid collisions). Show collision rate in the report.
	•	Create sources as a json array including one entry: "retailer:chewy" or "retailer:aadf" with the raw URL if available.

D) Staging Outputs (no production writes)

Create the following artifacts:
	1.	/reports/RETAILER_AUDIT_SUMMARY.md – Executive summary for both sources:
	•	Row counts per source, % dog vs non-dog, % toppers/treats
	•	Match rate vs our catalog (by brand_slug, by product_key fuzzy/on name)
	•	Coverage added if merged (Δ for form, life_stage, ingredients_tokens)
	•	Top 20 brands by potential impact (SKU × missing fields filled)
	2.	/reports/CHEWY_AUDIT.md and /reports/AADF_AUDIT.md – Deep dives:
	•	Field coverage tables (form, life_stage, ingredients, macros, price weight parsing)
	•	Known oddities (e.g., in Chewy JSON: brand under brand.slogan; specs embedded in “Specifications” text; units oz, lb)
	•	Parsing rules you used (regexes/heuristics), with 3–5 concrete examples each
	3.	/data/staging/retailer_staging.chewy.csv and /data/staging/retailer_staging.aadf.csv – Canonical-shaped rows ready for merge (one row per product), including a staging_source column (chewy/aadf) and staging_confidence (0–1).
	4.	/reports/RETAILER_MATCH_REPORT.md – How many map cleanly to existing foods_canonical by:
	•	Exact product_key
	•	Brand + fuzzy name (>0.85 similarity; list ambiguous clusters)
	•	Brand family + inferred series (if available)
	5.	/reports/RETAILER_RISKS.md – Risks & false-positive patterns (e.g., “Bowl Boosters topper misclassified as complete food”).
	6.	/sql/retailer_staging.sql – Optional DDL to create retailer_staging tables in Supabase (read-only review), not auto-executed.

E) Acceptance Gates (for future merge; do not merge now)

Compute and print pass/fail for each:
	•	Match Rate: ≥ 30% of rows can be matched confidently to existing products by brand_slug + fuzzy name or become clearly “new SKUs” (no duplicates).
	•	Quality Lift: If merged, would raise form and/or life_stage coverage by ≥ 10pp on PENDING/ACTIVE brands (show before/after by brand).
	•	Safety: 0 new duplicate product_key collisions in simulation; 0 invalid slugs; all arrays typed as JSON; no ingredients hallucination.
	•	Provenance: Every staged row has sources containing the retailer source and URL.

F) Delivery
	•	Print only the headline lines from RETAILER_AUDIT_SUMMARY.md at the end:
	•	Total rows per source
	•	Estimated safe-merge candidates
	•	Top 5 brands by potential impact
	•	Gate results (pass/fail)
	•	Provide a one-liner recommendation: MERGE-CHEWY, MERGE-AADF, MERGE-PARTIAL, or DO-NOT-MERGE, with a brief reason.

Reminder: This is an audit + staging pass. No writes to foods_canonical or published views. All outputs should be local files (and optional SQL for later review).