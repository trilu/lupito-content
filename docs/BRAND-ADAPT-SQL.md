“Adapt the SQL scripts for Supabase (enum, triggers, clean casts, correct coverage) and output final paste-ready SQL”

Goal
Rewrite the previously generated SQL so I can paste it into the Supabase SQL editor as three clean, idempotent scripts with the following fixes:

What to change (must do)
	1.	Allowlist status as ENUM + updated_at trigger
	•	Create enum type allowlist_status with values: ACTIVE, PENDING, PAUSED, REMOVED.
	•	brand_allowlist.status uses that enum (not VARCHAR).
	•	Create a simple trigger to auto-update updated_at on row updates.
	•	Keep initial seed rows (briantos, bozita as ACTIVE; alpha, belcando, brit as PENDING). Use ON CONFLICT DO NOTHING.
	2.	View-layer JSON casting under original column names
	•	In foods_published_prod and foods_published_preview, do not add *_json columns.
	•	Replace raw text/JSON columns with casts under the same names:
	•	ingredients_tokens::jsonb AS ingredients_tokens
	•	available_countries::jsonb AS available_countries
	•	sources::jsonb AS sources
	•	Preserve provenance fields (brand, product_name, brand_slug, etc.).
	•	Join to brand_allowlist and include allowlist_status in the view output.
	3.	Coverage metrics that reflect “has real data” (not “[]”)
	•	In the materialized views:
	•	ingredients_coverage = percentage of rows where jsonb_typeof(ingredients_tokens)='array' AND jsonb_array_length(ingredients_tokens) > 0.
	•	kcal_coverage = percentage where kcal_per_100g BETWEEN 200 AND 600 (use this same range for kcal_outliers: outside that range).
	•	price_coverage = percentage where price_per_kg_eur IS NOT NULL.
	•	price_bucket_coverage = percentage where price_bucket IS NOT NULL.
	•	completion_pct = average of: form, life_stage, ingredients, kcal, price (5 fields).
	4.	Sources for the two published views
	•	foods_published_prod = rows from foods_canonical JOIN allowlist WHERE status=‘ACTIVE’.
	•	foods_published_preview = rows from foods_canonical JOIN allowlist WHERE status IN (‘ACTIVE’,‘PENDING’).
	•	Do not mutate base tables; all normalization happens at the view layer.
	5.	Indexes (on underlying table)
	•	Keep/create indexes on foods_canonical for: (brand_slug), (brand_family) WHERE brand_family IS NOT NULL, (life_stage) WHERE life_stage IS NOT NULL, (form) WHERE form IS NOT NULL. Use IF NOT EXISTS.
	6.	Permissions (read-only for clients)
	•	Add GRANT SELECT on the two views and both MVs to the roles that the Admin and AI services use (typically anon and service role). If you can’t infer exact roles, include commented GRANT lines with placeholders.
	7.	Idempotency
	•	Scripts must be safe to re-run (i.e., CREATE TYPE IF NOT EXISTS, CREATE TABLE IF NOT EXISTS, CREATE MATERIALIZED VIEW IF NOT EXISTS, CREATE OR REPLACE VIEW, CREATE INDEX IF NOT EXISTS).
	•	No destructive operations.

Deliverables (what to output)

Please output three separate, paste-ready SQL blocks with clear headings:

SQL Script 1 — Allowlist (enum + trigger + seed)
	•	Create enum allowlist_status (IF NOT EXISTS).
	•	Create brand_allowlist (IF NOT EXISTS) with status allowlist_status.
	•	Create updated_at trigger/function.
	•	Seed initial rows with ON CONFLICT DO NOTHING.

SQL Script 2 — Published Views (prod + preview)
	•	CREATE OR REPLACE VIEW foods_published_prod AS ...
	•	CREATE OR REPLACE VIEW foods_published_preview AS ...
	•	Both views cast ingredients_tokens, available_countries, sources to jsonb under their original names.
	•	Include allowlist_status column.
	•	Create the underlying table indexes on foods_canonical (IF NOT EXISTS).

SQL Script 3 — Brand Quality Materialized Views
	•	CREATE MATERIALIZED VIEW IF NOT EXISTS foods_brand_quality_prod_mv AS ...
	•	CREATE MATERIALIZED VIEW IF NOT EXISTS foods_brand_quality_preview_mv AS ...
	•	Coverage calculations per rules above (ingredients array length > 0, kcal in [200..600], etc.).
	•	kcal_outliers = outside [200..600].
	•	REFRESH MATERIALIZED VIEW statements.
	•	(Optional) commented GRANT SELECT lines for the two views and two MVs.

Verification block (print after the SQL)

After the SQL blocks, print a short “source of truth” summary I can paste into other repos:
SUPABASE_URL = <masked-host>
ACTIVE_PROD_VIEW = foods_published_prod
ACTIVE_PREVIEW_VIEW = foods_published_preview
BRAND_QUALITY_MV_PROD = foods_brand_quality_prod_mv
BRAND_QUALITY_MV_PREVIEW = foods_brand_quality_preview_mv
JSON_ARRAYS_OK_RULE = jsonb_typeof(field)='array' AND jsonb_array_length(field)>0
KCALS_VALID_RANGE = 200..600
Constraints
	•	Do not execute anything; just output the final SQL text blocks and the source-of-truth summary.
	•	Assume schema public.
	•	Assume foods_canonical exists.

Acceptance
	•	The SQL is idempotent and ready to paste.
	•	Views expose arrays as proper jsonb under original names.
	•	MV coverage math reflects real data, not empty arrays.
	•	Source-of-truth block is present at the end.