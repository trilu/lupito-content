C1 — Build compat views (normalize each source)

Role: You’re in the Content repo (Supabase + scripts).
Goal: Normalize our 3 primary sources into a shared shape (no code pasted; you choose how).

Do:
	1.	Create/refresh compat views (or materialized views) for:
	•	food_candidates_compat
	•	food_candidates_sc_compat
	•	food_brands_compat
	2.	In each compat view, ensure these canonical columns are produced (normalized):
	•	product_key (brand_slug|name_slug|form)
	•	brand, brand_slug, product_name, name_slug, form
	•	life_stage in {puppy|adult|senior|all|null} (infer from names: senior|mature|7+; puppy|junior|growth; adult|maintenance; all life stages)
	•	kcal_per_100g; if missing but protein_percent & fat_percent present, compute Atwater estimate and set kcal_is_estimated=true
	•	protein_percent, fat_percent
	•	ingredients_tokens (lowercased, de-duplicated); derive primary_protein, has_chicken, has_poultry
	•	available_countries (array; include "EU" when EU-wide/likely EU)
	•	price_per_kg, price_bucket using thresholds: Low ≤ €3.5/kg; Mid €3.5–7.0; High > €7.0
	•	image_url, product_url, source, updated_at
	•	quality_score: +1 each for (life_stage known, kcal known/est, tokens present, form known, price known) +1 for specific life_stage −1 if kcal estimated
	3.	Output:
	•	Row counts for each compat view
	•	5 sample rows (brand, product_name, form, life_stage, kcal_known/est, primary_protein, has_chicken, available_countries, price_bucket)

    C2 — Union & de-dupe into foods_canonical + provenance

Role: Content repo.
Goal: One canonical table with the best row per product.

Do:
	1.	Create/refresh foods_union_all = UNION ALL of the three *_compat views.
	2.	Create/refresh foods_canonical (table) by deduplicating on product_key with this precedence:
	1.	kcal known > estimated > null
	2.	life_stage specific (puppy|adult|senior) > all > null
	3.	richer ingredients_tokens (longer array)
	4.	price_per_kg present > missing
	5.	higher quality_score
	6.	newest updated_at
	3.	Keep sources JSON listing contributing source rows/ids per product_key.
	4.	Output:
	•	Counts: union vs canonical
	•	Duplicates merged: number of product_key groups with >1 rows
	•	Before/after coverage deltas for: life_stage, kcal (known+est), tokens, availability, price

    C3 — Publish & index for AI

Role: Content repo.
Goal: Make AI read the canonical set efficiently.

Do:
	1.	Point foods_published view to select from foods_canonical with the columns the AI expects.
	2.	Add/confirm indexes:
	•	UNIQUE(product_key)
	•	btree on brand_slug, life_stage
	•	GIN on available_countries, ingredients_tokens
	3.	Output:
	•	Row count of foods_published
	•	Indexes created/confirmed (list)
	•	Note that AI can now read via CATALOG_VIEW_NAME=foods_published

    C4 — QA snapshot & sample

Role: Content repo.
Goal: Show we hit coverage targets.

Do:
	1.	Report (post-canonical, i.e., foods_canonical/foods_published):
	•	% life_stage known or all (target ≥95%)
	•	% kcal known + estimated (target ≥90%)
	•	% ingredients_tokens present (target ≥95%)
	•	% with "EU" or any country (target ≥90%)
	•	% with price_per_kg or bucket (may be low; report exact)
	2.	Provide 4 counts:
	•	Adult-suitable (adult|all|null) + EU available
	•	Senior-suitable (senior|all|null) + EU available
	•	Non-chicken (has_chicken=false) + EU available
	•	Dry vs Wet split for adult + EU available
	3.	Export catalog_sample.csv (50 rows) with: brand, product_name, form, life_stage, kcal_known/estimated, primary_protein, has_chicken, available_countries, price_bucket
	4.	Output: QA numbers + CSV path