Goal: Use the attached docs/ALL-BRANDS.md to (1) reconcile brand coverage, (2) fix any remaining brand normalization issues, (3) add brands we don’t have yet, and (4) refresh preview/prod views + scoreboards so Admin/AI see the correct universe.

Input file: docs/ALL-BRANDS.md (one brand per line; includes big brands like Royal Canin, Purina, Hill’s, etc.).

Do not paste code back. Implement end-to-end and return the reports.

1) Ingest & normalize the brand list
	•	Read ALL-BRANDS.md and normalize to brand_slug (snake_case) and display_name.
	•	Cross-reference with our brand_aliases / brand_phrase_map and extend it if needed (apostrophes, dashes, lines like “Pro Plan”, “Science Plan”, “Prescription Diet”).
	•	Produce reports/BRAND_LIST_IMPORT.md with a table: display_name | brand_slug | alias_hit (y/n) | notes.

2) Reconcile against catalog
	•	For each brand_slug from the list, compute current presence and quality in preview and prod catalogs:
	•	sku_count, form_cov, life_stage_cov, ingredients_cov, kcal_cov, price_cov, completion_pct, kcal_outliers.
	•	Output reports/BRAND_LIST_RECONCILIATION.md with columns above + a status (ACTIVE/PENDING/MISSING).
	•	Flag MISSING (in list but not in catalog), PARTIAL (present but below gates), and ACTIVE (meets gates and is allowlisted).

3) Fix remaining brand issues (normalization pass)
	•	Run the brand normalization engine across all source/compat tables (not just pilot): fix split/fragment brands, brand+line prefixes, apostrophe variants, and rebuild brand_slug, name_slug, and product_key; then dedupe.
	•	Ensure idempotency and re-run QA guards (no orphan fragments, no off-brand slugs, no duplicate keys).
	•	Refresh canonical/published views and brand quality MVs.
	•	Deliver reports/BRAND_NORMALIZATION_DELTA.md (before→after counts, merges, examples).

4) Add brands we don’t have (queue for harvest)
	•	For MISSING brands from the list, create entries in a brand_registry (or extend existing table) with fields: brand_slug, display_name, priority_weight (default 1.0), status=PENDING, first_seen_source='ALL-BRANDS.md'.
	•	Build a harvest queue reports/NEW_BRANDS_QUEUE.md ordered by priority:
	•	Default priorities: royal_canin=3.0, purina=3.0, hills=2.5, others 1.0 (adjust if we already have them).
	•	Include suggested seed URLs (official pages) and any robots/anti-bot notes.

5) Update allowlist + scoreboard (no promotions yet)
	•	Keep existing ACTIVE brands unchanged.
	•	Add new brands as PENDING only; don’t promote.
	•	Refresh foods_brand_quality_preview_mv and …_prod_mv; regenerate reports/FOODS_BRAND_SCOREBOARD.md.

6) Wire through catalogs & verify
	•	Ensure preview reads from foods_published_preview, prod from foods_published_prod.
	•	Confirm brand counts differ where expected (preview > prod).
	•	Produce reports/CATALOG_VERIFICATION.md with: distinct brands (preview vs prod), total rows, and top 10 brands by SKU for each view.

7) Deliverables to paste back
	•	BRAND_LIST_RECONCILIATION.md — presence/quality per brand.
	•	BRAND_NORMALIZATION_DELTA.md — what changed and proof QA guards pass.
	•	NEW_BRANDS_QUEUE.md — prioritized list of missing brands to harvest next.
	•	CATALOG_VERIFICATION.md — preview vs prod brand/row summary.

Success criteria
	•	All list brands appear as ACTIVE/PENDING/MISSING with clear next action.
	•	No brand normalization regressions; QA guards pass.
	•	Preview/prod views refreshed and counts updated.
	•	A concrete, prioritized harvest queue exists for MISSING/PARTIAL brands.

⸻

The attached list includes many UK/EU brands (e.g., Royal Canin, Purina, Hill’s, Orijen, Acana, Carnilove, Eukanuba, Taste of the Wild, Lily’s Kitchen, Harringtons, etc.), so please make sure the alias map captures multi-word brands and lines (e.g., “Hill’s Science Plan”, “Purina Pro Plan”, “Royal Canin Veterinary Diets”).