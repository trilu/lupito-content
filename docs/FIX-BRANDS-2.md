Task name: “Split-Brand Fix — Full Catalog Scan, Apply, Guard”

Do the following, in order, and don’t paste code back — just implement and report:
	1.	Scan the right places
	•	Re-run split-brand discovery across all source tables & compat views, not only the pilot set:
include food_candidates, food_candidates_sc, food_brands, any food_products* tables, and the union view (e.g., foods_union_all or equivalent).
	•	Produce an updated reports/BRAND_SPLIT_CANDIDATES.md with per-table counts and 20 sample rows per pattern (e.g., Royal|Canin …, Hills|Science Plan …, Purina|Pro Plan …).
	•	Explicitly list tables with non-zero findings.
	2.	Wire normalization into the pipeline
	•	Make split-brand normalization an explicit step before canonical key build and dedupe:
	•	Option A (preferred): apply inside each source’s compat view so the union always receives normalized brand + cleaned product_name.
	•	Option B: apply in the canonical ETL right after union, before key/slug derivation.
	•	Ensure the step is idempotent (no double-stripping on re-runs).
	3.	Finish QA guards (SQL)
	•	Add guard queries under sql/qa/BRAND_SPLIT_GUARDS.sql that must pass for published views:
	•	No product_name beginning with the second token of known multi-word brands when brand_slug equals the canonical (e.g., no '^Canin\\b' with brand_slug='royal_canin'; protect against “Canine” via word boundary and denylist).
	•	No off-brand slugs like ^royal(?!_canin)$, ^purina_(?!pro_plan|one)$, ^hills(?!$) unless modeled via a brand_line column.
	•	Zero unexpected product_key collisions (aside from logged merges).
	4.	Apply safely
	•	Take snapshots of impacted tables/views.
	•	Run normalization with --apply for only the tables flagged in step 1.
	•	Rebuild slugs/keys, run dedupe merges (log counts & examples), refresh MVs (foods_brand_quality_*, published views).
	5.	Report before/after
	•	Update:
	•	reports/BRAND_SPLIT_BEFORE.md → counts of split patterns, distinct brand_slugs, example rows.
	•	reports/BRAND_SPLIT_AFTER.md → the same, plus: # merges, brand_slug consolidation deltas, and confirmation that QA guards pass.
	•	reports/BRAND_GLOSSARY.md → include brand_line (e.g., pro_plan, science_plan) where extracted.
	•	Call out Royal Canin, Hill’s, Purina specifically with before/after SKU counts under the unified brand_slug.
	6.	Prevent regressions
	•	Add a nightly lightweight check that fails CI if any guard query returns rows.
	•	Keep/extend data/brand_phrase_map.csv (include diacritics, e.g., “Hill’s” vs “Hills”; add denylist for “Canine”).

Definition of done
	•	Split-brand rows fixed across all sources; brand_slug unified (e.g., royal_canin, hills, purina).
	•	No product names start with orphaned fragments (“Canin …”, “Science Plan …”, “Pro Plan …”).
	•	Keys/slugs rebuilt; duplicates merged; QA guards all passing.
	•	Before/after reports attached and MVs refreshed.