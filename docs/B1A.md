Goal: Switch to a staging → server-side merge so new products are created safely and updates are auditable.
Do (no code pasted back):
	1.	Create staging: Add table foods_ingestion_staging with columns: run_id, brand, brand_slug, product_name_raw, name_slug, product_key_computed, product_url, ingredients_raw, ingredients_tokens, ingredients_language, ingredients_source, ingredients_parsed_at, extracted_at, plus a JSON debug blob.
	2.	Writer change: Writer only INSERTS rows into staging (never touches foods_canonical). Use a consistent run_id.
	3.	Server merge function: Build a single SQL/PLpgSQL merge routine the job can call with run_id that:
	•	Joins staging→foods_canonical by product_key. If no hit, fallback to (brand_slug, name_slug).
	•	If still no hit and brand_slug is ACTIVE/PENDING in brand_allowlist, INSERT a new minimal canonical row (brand, product_name, brand_slug, name_slug, product_key, sources).
	•	UPDATE only fields that are null/empty in canonical: ingredients_raw, ingredients_tokens, ingredients_language, ingredients_source, ingredients_parsed_at. Never overwrite non-null canonical values.
	•	Emit counters: inserted, updated, skipped (by reason).
	4.	Run on B1 batch: Stage the Bozita/Belcando/Briantos extractions and call the merge.
	5.	Refresh MVs and produce INGREDIENTS_LIFT_REPORT.md: brand-level before/after, MERGE counters, and a 10-row sample diff.
	6.	Residuals pass: For any staging rows that still didn’t merge, print a RESIDUALS.md with why (e.g., brand not allowlisted; key mismatch). If key mismatch, propose entries for a tiny mapping table (product_key_override_map) but do not apply them yet.
	7.	Guardrails: Add run-health checks: if extracted ≥50 but (inserted+updated)==0, fail the run. Log a one-line summary at the end of every run.
Acceptance: Ingredients coverage lifts materially for Bozita/Belcando in foods_published_preview; MERGE counters show non-zero inserts/updates; re-running the same run_id is idempotent.