“Prod coverage mini-sprint (ACTIVE only)”

Goal: Boost briantos and bozita to the gates above and verify in the MVs.

Do (no code pasted back):
	1.	Refresh metrics and print a one-page delta:
	•	Read foods_brand_quality_prod_mv (and the underlying foods_published_prod) for briantos, bozita.
	•	Compute current coverage vs targets for: ingredients_tokens (non-empty), form, life_stage, kcal valid range.
	•	List exact SKU IDs missing each field (max 25 per field per brand), and the suspected reason (e.g., “snapshot exists but parser has no match,” “PDF only,” “language mismatch”).
	2.	Harvest & parse only ACTIVE brands using the existing snapshot → parse → server-side merge flow (the same safe “B1A” pattern):
	•	Re-use GCS snapshots (re-capture only where missing).
	•	Re-run ingredient extraction with the improved selectors; record ingredients_source and ingredients_parsed_at.
	•	Upsert via server-side merge; idempotent; no duplicates.
	3.	Recompute coverage and print a simple before → after table for both brands plus a “Food-ready” count (meets all gates).
	4.	Output:
	•	A short ACTION/RESULTS block with (a) SKUs fixed, (b) SKUs still blocked + reason buckets, (c) concrete recommendation (e.g., “Bozita PASS; Briantos needs PDF pass for 12 SKUs”).
	•	Do not modify allowlist status yet—just recommend.