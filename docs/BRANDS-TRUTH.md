Ground truth on Supabase + family/series from canonical brand slugs

Objective: Make all brand presence & family logic run on live Supabase views (not CSV), keyed by brand_slug (not product-name substrings), with no row limits. Deliver verifiable evidence.

Tasks:
	1.	Grounding check (live DB, not CSV)
	•	Print masked connection info (host fingerprint, database).
	•	Confirm existence of both views: foods_published_prod and foods_published_preview. If missing, state exact fallback used.
	•	Remove any row caps (must scan all rows).
	2.	Brand truth = brand_slug (never name substrings)
	•	All brand counts, presence checks, and leaderboards must key on brand_slug (and canonical brand mapping), not product name tokens.
	•	Create/ensure a single canonical brand map (table or YAML) used everywhere (consolidate e.g., arden→arden_grange, barking→barking_heads, royal/royal_canin_*→royal_canin, etc.).
	3.	Family & series in the published views
	•	Compute brand_family + series at the view layer (do not mutate base tables).
	•	Keep core fields (brand, product_name, brand_slug) as provenance alongside brand_family and series.
	4.	JSON array gate
	•	Ensure ingredients_tokens, available_countries, sources are jsonb arrays in both published views (cast in views if needed).
	•	Report % rows passing the array-type check.
	5.	Evidence pack (from live SQL only)
	•	PHASE_A_GROUNDING_SUPABASE.md: connection proof, which views used.
	•	BRAND_TRUTH_AUDIT.md: top 20 brands by brand_slug (counts), plus 20-row witnesses per flagged “big” brand (Royal Canin, Hill’s, Purina) showing brand, brand_slug, product_name.
	•	FAMILY_SERIES_COVERAGE_SUPABASE.md: % coverage for brand_family and series in both prod & preview views.
	•	Update brand quality MVs/scoreboards to include brand_family rollups in addition to brand_slug.

Acceptance gates (must pass):
	•	Reports explicitly say which view was queried and show no row caps.
	•	All presence/leaderboard logic uses brand_slug (not name substrings).
	•	brand_family non-null in ≥95% of rows; series populated for the major families you can detect.
	•	JSON array gate: ≥99% rows are typed arrays in both published views.