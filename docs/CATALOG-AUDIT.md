Goal: Run a comprehensive, read-only audit across all food tables/views we use so we can see every data issue (brand/line splits, stringified arrays, kcal/life-stage gaps, price anomalies, slug hygiene, duplicates), with a Royal Canin deep dive and clear fix proposals. Do not modify data—just analyze and report.

Scope

Scan these if present (use “if exists” logic):
	•	Sources: food_candidates, food_candidates_sc, food_brands, food_raw
	•	Canonical/Compat: any *_compat views, foods_canonical, foods_canonical_norm
	•	Published: foods_published, foods_published_preview, foods_published_prod
	•	Quality & Allowlist: foods_brand_quality_* (views/MVs), brand_allowlist (if present)

What to detect (key checks)
	1.	Brand & line normalization
	•	Count distinct brand / brand_slug per table.
	•	Detect split/fragment patterns: multi-word brands split between brand and leading product_name tokens (e.g., brand='Royal', product_name='Canin …').
	•	Detect brand families / lines living as separate brands (e.g., royal_canin_breed, royal_canin_size, purina_pro_plan, hills_science_plan, hills_prescription_diet).
	•	Propose canonical brand + product_line extraction (parent brand stays in brand, line in product_line).
	2.	Type integrity
	•	Find fields that should be arrays/JSON but are stringified (e.g., ingredients_tokens = '[]', available_countries = '["UK"]').
	•	List columns per table with their actual data types (via catalog) + sample offending values.
	3.	Nutrition coverage & outliers
	•	Coverage of kcal_per_100g, protein_percent, fat_percent.
	•	Kcal outliers: < 40 or > 600 kcal/100g.
	•	Where kcal is null but macros exist, flag as “estimable”.
	4.	Life stage / form coverage
	•	Coverage of life_stage and form.
	•	Inference opportunities from product_name (e.g., “Puppy”, “Adult”, “Senior”, “Ageing 8+”; “dry/wet/freeze-dried/raw”).
	5.	Price integrity
	•	Coverage of price_per_kg_eur.
	•	Detect pack/weight tokens in product_name (e.g., 2 × 12 kg, 3kg, 400 g) and whether total_weight_g is derived.
	•	Outliers: price_per_kg_eur > 100 or < 1.
	6.	Allergen signal
	•	Coverage of ingredients_tokens.
	•	Check allergen flags (e.g., has_chicken) are not default false when tokens are empty—should be null/unknown.
	7.	Slug & key hygiene
	•	name_slug and brand_slug contain only [a-z0-9_-] (no +, em dashes, etc.).
	•	Product key collisions: same identity across multiple rows; show duplicate clusters.
	8.	Published view health
	•	For foods_published_* views, show Food-ready counts (your gates: form ≥95%, life_stage ≥95%, kcal sane, ingredients tokens present, price bucket if available).
	•	Compare preview vs prod: total rows, distinct brands, top 10 brands by SKU.

Special deep dive: Royal Canin
	•	Show all brand_slug variants mapping to Royal Canin (e.g., royal_canin_breed, royal_canin_size, royal_canin_care_nutrition, royal_canin_veterinary).
	•	Count SKUs per variant and in published views.
	•	Measure issues in RC rows: stringified arrays, missing kcal/life_stage, price outliers, leading “Canin ” prefixes, non-sanitized slugs, allergen defaults.
	•	Propose canonicalization: brand = Royal Canin, brand_slug = royal_canin, product_line = breed|size|care_nutrition|veterinary, plus size_line if tokens like Mini/Maxi.

Outputs (write these files)
	•	reports/GLOBAL_DATA_HEALTH.md
– Table list, row counts, field coverage (kcal/form/life_stage/ingredients/price), outliers, type integrity issues, slug/key hygiene, per-brand metrics.
	•	reports/ROYAL_CANIN_DEEP_DIVE.md
– RC brand variants, counts, concrete anomalies with 20 sample rows, and a canonicalization plan table.
	•	reports/ANOMALY_SUMMARY.md
– Deduped list of anomalies with counts by table (stringified arrays, split brands, invalid slugs, kcal/price outliers, allergen defaults).
	•	reports/TOP_FIX_WINS.md
– “Top 10 highest-impact fixes” ranked by SKU affected × severity (e.g., “Convert stringified arrays in foods_published_prod: 1,240 rows”).
	•	reports/BRAND_FAMILY_MAP_PROPOSALS.csv
– Machine-readable proposals: canonical_brand_slug, product_line, match_pattern, confidence, sample_count.
	•	reports/DUPLICATE_KEYS.csv
– Clusters of product_key collisions (brand_slug, name_slug, form, count, example ids).
	•	reports/TABLE_FIELD_TYPES.md
– For every scanned table: column name, data type, % null, sample offending values.
	•	reports/CATALOG_COMPARE_PREVIEW_PROD.md
– Preview vs prod: brand counts, total rows, top brands by SKU, Food-ready counts.

Deliver a short exec summary back

At the end, paste a short “EXEC SUMMARY” with:
	•	5 biggest issues (one-liners with counts)
	•	5 quickest wins (one-liners)
	•	Confirmation whether Royal Canin SKUs are split and how many can be unified
	•	Where stringified arrays exist (table/column + row count)
	•	Whether preview vs prod differ as expected

Important: This is an analysis-only pass. Don’t mutate data or views yet. We’ll approve the fix plan after seeing the reports.