Prompt 0 — Safety & Snapshot

“Run a read-only snapshot before any changes:
	•	Identify every live table/view we touch: foods_canonical, foods_published, foods_published_preview, foods_published_prod, foods_union_all, food_candidates, food_candidates_sc, food_brands, food_raw.
	•	For each: row count, last updated, sample 10 rows with these columns if present: brand, brand_slug, product_name, name_slug, ingredients_raw, ingredients_tokens, kcal_per_100g, protein_percent, fat_percent, life_stage, form, sources, available_countries.
	•	Export a timestamped backup CSV per table to /backups/ingredients_preflight/ and save a short PRECHECK.md with counts.
	•	Do not modify data in this step. If any required credentials are missing, pause and ask me.”

Prompt 1 — Ingredients Field Audit & Type Fix (no data loss)

“Perform a catalog-wide audit of ingredients fields and fix types safely:
	•	Detect where ingredients_tokens is a stringified array instead of JSONB. Count how many rows per table.
	•	Standardize to JSONB arrays across all relevant tables/views. Create idempotent SQL migrations that:
	•	Convert valid "[...]" strings → jsonb arrays,
	•	Replace invalid/empty → []::jsonb,
	•	Never overwrite properly typed arrays.
	•	Add/confirm these metadata fields where useful: ingredients_tokens_version (e.g., v1), ingredients_parsed_at (timestamp), ingredients_source (label|html|pdf|manual), ingredients_language (BCP-47 if detectable).
	•	Write a diff report: rows fixed per table, % coverage with non-empty arrays, top 50 most common tokens (post-fix) for sanity check.
	•	Refresh affected views/materialized views. Save report as /reports/INGREDIENTS_TYPE_FIX.md.”

Prompt 2 — Tokenize + Canonicalize + Allergen Map (quality first)

“Rebuild ingredients processing for quality:
	•	Create/extend a canonical ingredient map (synonyms → canonical token). Examples: ‘chicken meal’, ‘dehydrated chicken’ → chicken; ‘maize’ → corn; ‘linseed’ → flax; etc. Store in data/ingredients_canonical_map.(yaml|csv) with at least 200 common entries.
	•	Retokenize all rows: clean punctuation, unify case, split on commas/‘and’, flatten parentheses, map synonyms → canonical tokens. Persist to ingredients_tokens (JSONB array). Keep original text in ingredients_raw.
	•	Build/update allergen taxonomy (chicken, poultry, beef, lamb, pork, fish, salmon, tuna, turkey, egg, dairy, soy, pea/legume, corn/maize, wheat, rice, barley, oats, yeast, flax). Derive allergen_groups (JSONB) from tokens.
	•	Produce coverage metrics: % rows with non-empty ingredients_tokens, % rows mapped to ≥1 allergen group, top 100 tokens, and a list of unmapped terms (to improve the map).
	•	Save /reports/INGREDIENTS_CANONICALIZATION.md + an ‘unmapped_terms.csv’ we can iterate on.”

Prompt 3 — Manufacturer Enrichment (ingredients + macros + kcal only)

“Run manufacturer-first enrichment for 10 high-impact brands (from our scoreboard):
	•	Crawl brand product pages and PDF datasheets (prefer PDFs for macros/kcal). Respect robots and rate limits.
	•	Extract:
	•	ingredients_raw (text) → retokenize via our pipeline,
	•	protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent (as-fed, numeric + qualifier if min/max),
	•	kcal_per_100g (label value if available),
	•	life_stage (puppy|adult|senior|all) and form (dry|wet|freeze_dried|raw), inferred from name/spec lines.
	•	When kcal missing, derive with modified Atwater using as-fed macros; set kcal_source='derived' (otherwise label) and clamp to form-specific safe ranges (dry 200–600; wet 50–150).
	•	Write provenance into sources (URL + source_type: html|pdf) and stamp ingredients_source accordingly.
	•	Upsert into the canonical layer with no price fields and no brand substring logic (use brand_slug only).
	•	Produce /reports/MANUFACTURER_ENRICHMENT_RUN.md with per-brand coverage lift for ingredients/macros/kcal, and a list of products still missing macros/kcal.”

Prompt 4 — Classification Tightening (form + life stage)

“Improve form and life_stage classification:
	•	Use name/series/description/spec to label form and life_stage. Add brand-specific rules where needed (e.g., ‘Mini Puppy’ → puppy, dry).
	•	Recompute coverage: target ≥95% for both in ACTIVE+PENDING brands.
	•	Store classification provenance: form_source, life_stage_source (rules|label|pdf|inferred).
	•	Save /reports/CLASSIFICATION_COVERAGE.md with before/after metrics and a list of ambiguous cases for manual review.”

Prompt 5 — Rebuild Published Views (price-free completion)

“Rebuild published layers and quality views without price dependency:
	•	Keep brand_allowlist as the gate. Ensure:
	•	foods_published_prod = ACTIVE brands,
	•	foods_published_preview = ACTIVE + PENDING.
	•	Recompute quality materialized views so completion% averages: ingredients coverage, macros pair (protein_percent & fat_percent), kcal coverage (label or derived), life_stage, form. Exclude price entirely.
	•	Add badges in the view data:
	•	kcal_source (label|derived),
	•	ingredients_quality_score (simple score from tokens_count + % mapped to canonical tokens).
	•	Refresh MVs and write /reports/PUBLISHED_VIEWS_REFRESH.md showing row counts and coverage by brand.”

Prompt 6 — Quality Gates & Outliers

“Run final quality gates on ACTIVE + PENDING brands (no price):
	•	Gates:
	•	Ingredients coverage ≥ 95%
	•	Macros (protein+fat) coverage ≥ 90%
	•	Kcal coverage ≥ 90% (label or derived)
	•	Form ≥ 95%, Life stage ≥ 95%
	•	Outliers = 0 (kcal per form range)
	•	Output brand scoreboard with PASS/NEAR/TODO, and a CSV of failures with exact reasons (which gate failed).
	•	Save /reports/QUALITY_GATES_SUMMARY.md and brand_gate_failures.csv.”

Prompt 7 — Promote READY brands & Roadmap

“Based on the gates, suggest brand promotions:
	•	List brands PENDING → READY for ACTIVE (production) with a one-liner justification per brand.
	•	Output the SQL to update brand_allowlist for agreed promotions (do not execute until I confirm).
	•	Propose the next Top-10 brands to enrich (highest impact by SKU × (100−completion%)).
	•	Save /reports/PROMOTION_PROPOSALS.md with the SQL block and the prioritized roadmap.”