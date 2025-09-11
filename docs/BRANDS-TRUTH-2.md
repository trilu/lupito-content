“Create & verify foods_published_prod and _preview in Supabase (single source of truth)”

Goal: Ensure our Supabase has the two published views we’ve been using conceptually:
	•	foods_published_prod (only ACTIVE brands via allowlist)
	•	foods_published_preview (ACTIVE + PENDING brands)

Then verify counts, arrays, and brand presence (RC/Hill’s/Purina), and output a copy-paste “source of truth” block.

Do this:
	1.	Grounding & inventory
	•	Print masked Supabase connection (host fingerprint + DB name).
	•	List all relations in public whose names start with foods_% (type + row counts).
	•	Confirm whether these exist:
	•	foods_published_prod (VIEW)
	•	foods_published_preview (VIEW)
	•	foods_brand_quality_prod_mv (MATERIALIZED VIEW)
	•	foods_brand_quality_preview_mv (MATERIALIZED VIEW)
	2.	Identify the canonical source
	•	Locate the most complete, unified source we built earlier (in this order of preference):
foods_canonical → foods_published_unified → foods_published_v2 → foods_published
	•	Show which one you selected and why.
	3.	(Re)create the allowlist table if needed
	•	Ensure brand_allowlist exists (columns: brand_slug, status ENUM: ACTIVE/PENDING/PAUSED/REMOVED, timestamps, notes).
	•	If it doesn’t exist, create it and insert the current known states (at minimum set briantos and bozita to ACTIVE; alpha, belcando, brit to PENDING).
	•	Print current allowlist snapshot.
	4.	Create the two published views (view-layer only; do NOT mutate base tables)
	•	foods_published_prod = SELECT from the canonical source JOIN allowlist WHERE status = ‘ACTIVE’.
	•	foods_published_preview = same but WHERE status IN (‘ACTIVE’,‘PENDING’).
	•	In both views:
	•	Cast ingredients_tokens, available_countries, and sources to jsonb so they’re proper arrays.
	•	Preserve provenance fields (brand, product_name, etc.).
	•	Include any computed normalization columns we rely on (brand_slug, brand_family, series, price_bucket, etc.).
	•	Add sensible indexes (on brand_slug, brand_family, life_stage, and form) if needed via underlying tables or created helper indexes.
	5.	(Re)build brand quality MVs
	•	Create/refresh:
	•	foods_brand_quality_prod_mv — reads from foods_published_prod
	•	foods_brand_quality_preview_mv — reads from foods_published_preview
	•	Each MV should expose: brand_slug, sku_count, coverage metrics (form, life_stage, ingredients, kcal, price, price_bucket), completion_pct, kcal_outliers, last_refreshed_at, and status from allowlist.
	6.	Verification (no CSV, full SQL)
	•	Row counts for both views.
	•	Distinct brand counts for both views.
	•	Witness samples (20 rows each) for Royal Canin, Hill’s, Purina by brand_slug only (no substring matches). If zero, say “absent in this view”.
	•	JSON array typing check: % rows where jsonb_typeof(ingredients_tokens)='array' (target ≥99% for both views).
	•	Print top-20 brands by brand_slug for both views.
    	7.	Output a “source of truth” block (copy-paste)
        SUPABASE_URL = <masked-host>
ACTIVE_PROD_VIEW = foods_published_prod (rows = NNNN)
ACTIVE_PREVIEW_VIEW = foods_published_preview (rows = MMMM)
BRAND_QUALITY_MV_PROD = foods_brand_quality_prod_mv
BRAND_QUALITY_MV_PREVIEW = foods_brand_quality_preview_mv
JSON_ARRAYS_OK = prod: XX.X% • preview: YY.Y%
NOTE = Allowlist gating applied at view layer
Acceptance gates (must pass):
	•	Both views exist with non-zero rows and correct allowlist semantics (prod ⊆ preview).
	•	Arrays are typed as jsonb arrays in both views (≥99%).
	•	Top-20 brand lists are printed for both views.
	•	The “source of truth” block is included and ready to paste into AI/Admin repos.
    