Prompt 1 — Quality Lockdown: Ground truth & safety rails

Goal: Prove we’re reading live Supabase correctly, nail down truth rules, and take a fresh snapshot.
Do:
	1.	Connect to Supabase and confirm the presence + row counts of: foods_canonical, foods_published_preview, foods_published_prod, brand_allowlist, foods_brand_quality_preview_mv, foods_brand_quality_prod_mv. Print counts.
	2.	Reassert “brand_slug is the only truth”: ensure no substring brand matching is used anywhere in analysis/enrichment. If any helper still does that, flag it and switch to brand_slug.
	3.	Run a type audit on ingredients_tokens, available_countries, sources across foods_canonical and both published views; report exact counts that are jsonb arrays vs stringified, and fix if needed.
	4.	Produce a LOCKDOWN REPORT with: table counts, array typing status, a short “truth rules” section, and a timestamped snapshot label we’ll reuse in subsequent reports.

⸻

Prompt 2 — Split-brand re-scan & canonicalization (full catalog)

Goal: Re-detect and correct brand splits (e.g., “Royal | Canin”) across the entire dataset, but only to set the brand_slug at ingestion/canonical level—never used downstream for matching.
Do:
	1.	Re-run the split-brand detector over all rows in foods_canonical and foods_union_all.
	2.	Compare against our brand_phrase_map/canonical_brand_map. Add any new patterns (e.g., “Hill’s | Science Plan”, “Purina | Pro Plan”, “Taste | of the Wild”).
	3.	Apply fixes only where the current brand_slug is clearly wrong or empty; produce a DELTA sheet: before→after (id, brand, product_name, old_brand_slug, new_brand_slug, reason, provenance).
	4.	Rebuild foods_canonical (or issue a consistent UPDATE pass) and do not push to Prod yet—this is for Preview validation.

⸻

Prompt 3 — Re-run enrichment (form, life_stage, allergens, pricing)

Goal: Lift coverage to our gates in Preview only.
Do:
	1.	Form & life_stage: Re-run the NLP classification with enhanced rules (multi-language keywords, brand-specific cues, description parsing). Print coverage deltas per brand.
	2.	Allergens: Re-apply allergen mapping from ingredients_tokens with a fresh dictionary pass; show coverage and top allergens found.
	3.	Kcal sanity: Validate kcal_per_100g inside [200..600]. Flag outliers and suggest fixes (re-parse source, or estimate from macros if safe).
	4.	Price: Extract pack size → compute price_per_kg_eur → compute price_bucket. Show % coverage per brand.
	5.	Output a PREVIEW ENRICHMENT REPORT: before/after coverage for form, life_stage, ingredients, kcal-valid, price, price_bucket; list any brands still failing.

⸻

Prompt 4 — Recompose Preview views & refresh metrics

Goal: Make Preview the single source for validation, then compute brand metrics.
Do:
	1.	Rebuild foods_published_preview from the updated canonical layer, preserving jsonb types and adding allowlist_status.
	2.	Refresh foods_brand_quality_preview_mv.
	3.	Generate a Brand Scoreboard (Preview) sorted by completion_pct desc and sku_count desc. Include PASS/NEAR/TODO status per brand using our gates.

⸻

Prompt 5 — Acceptance gates & go/no-go for promotion

Goal: Decide what gets promoted from Preview → Prod safely.
Do:
	1.	Check Food-ready gates per brand (Preview):
	•	life_stage ≥ 95%
	•	form ≥ 90%
	•	ingredients_coverage ≥ 85%
	•	kcal_valid (200..600) ≥ 90%
	•	kcal_outliers = 0
	2.	Produce a PROMOTION CANDIDATES list (brands meeting all gates).
	3.	For each candidate, draft a single SQL statement to update brand_allowlist to ACTIVE and then refresh MVs. Do not execute—just print.
	4.	Emit a GO/NO-GO summary: how many SKUs will Prod gain, and confirm Food will never be empty after promotion.

⸻

Prompt 6 — Royal Canin/Hill’s/Purina probes (truth checks)

Goal: Ensure we’re not faking presence via substring.
Do:
	1.	Run witness queries that count rows in Preview/Prod strictly by brand_slug IN ('royal_canin','hills','purina','purina_one','purina_pro_plan').
	2.	If counts are 0, explicitly say “Not harvested yet—correct.” If non-zero, list top 10 product_name with brand_slug and confirm they’re real.
	3.	Add any new split patterns to the map only if they fix brand_slug assignment; never to “find” brands by name substrings.

⸻

Prompt 7 — Final “Preview → Prod sync” (once gates pass)

Goal: Promote safely and verify.
Do:
	1.	Execute the allowlist promotions from Prompt 5 (only the ones we approved).
	2.	Refresh foods_published_prod and foods_brand_quality_prod_mv.
	3.	Output a Prod vs Preview diff: brands, rows, and coverage.
	4.	Print a final acceptance sheet with SKUs now available in Prod for adult/puppy/senior dry food.