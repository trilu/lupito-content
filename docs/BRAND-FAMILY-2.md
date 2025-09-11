Ground it in Supabase, then fix split brands (RC, Hill’s, Purina)

Goal: Prove we’re querying the live Supabase catalog (not CSV), then normalize split-brand artifacts (e.g., brand=royal, name=Canin …) across the published views. Deliver before/after evidence and keep base tables untouched (view-level fixes).

Phase A — Grounding check (live DB, not CSV)
	1.	Print the Supabase connection you’re using without secrets (mask keys, show host fingerprint and database).
	2.	Query the active catalog view we’ve standardized on:
	•	Preview: foods_published_preview
	•	Prod: foods_published_prod
Confirm both exist; if not, say exactly which fallback you used.
	3.	Run witness counts directly against the live view (no exports):
	•	Rows where brand ILIKE 'royal%' OR name ILIKE '%royal%canin%'
	•	Same for Hill’s (hills/hill’s/science plan/prescription diet) and Purina (pro plan/one/dog chow/veterinary)
	4.	Return: brand list sample (20 rows) for each of RC/Hill’s/Purina showing brand, product_name, brand_slug, name_slug.

Acceptance: I see non-zero live counts (or a zero with a credible reason), and the output explicitly states which view was read.

Phase B — Split-brand normalization v2 (view-level)

Implement normalization in the published views (not by rewriting base rows):
	•	Detect split pattern: brand is a single token that equals the first token of the product name’s remaining brand token, e.g.
	•	brand='royal' AND LOWER(name) starts with 'canin ' → canonical brand = Royal Canin (family: royal_canin, series derived by rules).
	•	brand IN ('hills','hill’s','hills science plan') → map to family hills and set series to science_plan or prescription_diet based on name keywords.
	•	brand='purina' + name contains pro plan/one/dog chow/vet keywords → family purina, series accordingly.
	•	Do not mutate base tables. Add computed columns (or override existing) in the view layer:
	•	brand_family (e.g., royal_canin, hills, purina)
	•	series (e.g., breed, size, care, veterinary for RC; science_plan/prescription_diet for Hill’s; pro_plan/one/dog_chow/veterinary for Purina)
	•	Keep original brand and product_name for provenance.
	•	Ensure ingredients_tokens, available_countries, and sources are jsonb arrays in the final views (cast if needed).

Phase C — Evidence pack

Produce these artifacts (from Supabase, not CSV):
	•	BRAND_FAMILY_BEFORE_AFTER.md: per brand/family counts before vs after (RC/Hill’s/Purina highlighted).
	•	ROYAL_CANIN_CONSOLIDATION.md: RC witness sample (20 rows) showing old→new brand/family/series.
	•	FAMILY_SERIES_COVERAGE.md: % coverage for brand_family and series in the published views.
	•	Guardrail query output: top 10 brands by SKU after normalization, and confirmation that the published view names used were foods_published_preview and foods_published_prod.

Acceptance gates (must pass)
	•	Live DB verified (host fingerprint + view names printed).
	•	RC appears with non-zero count and is consolidated under brand_family='royal_canin'.
	•	Hill’s split across Science Plan / Prescription Diet series as expected.
	•	Purina split across Pro Plan / ONE / Dog Chow / Veterinary series as expected.
	•	brand_family non-null on ≥95% of rows; series non-null on ≥60% of affected families.
	•	JSON array gate: ≥99% arrays are properly typed in the published views.