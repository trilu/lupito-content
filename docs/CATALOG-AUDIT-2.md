Master Coverage & Consolidation — Fix Pack V2 (ALL food tables)

Goal: apply the same data fixes (types, slugs, duplicates, brand normalization) across every active food table/view, then re-compose a single, trustworthy pipeline (foods_union_all → foods_canonical → foods_published_preview/prod) and prove coverage with reports.

Do not paste code back. Execute end-to-end and return reports.

Scope
	•	Include anything named like: food_%, foods_% (examples from our DB list):
food_brands, food_brands_compat, food_brands_sc, food_candidates, food_candidates_compat, food_candidates_sc, food_candidates_sc_brand_coverage, food_candidates_sc_by_retailer, food_candidates_sc_compat, food_candidates_sc_complete, food_change_statistics, food_changes, food_consumption, food_inventory, food_products, food_products_sc, food_raw, foods_canonical, foods_published, foods_union_all.
	•	Treat “_sc”, “_compat”, “_complete”, “_canonical”, “_published”, and “_union_all” as part of the lineage.
	•	Use IF EXISTS guards; no destructive drops. Take dated snapshots for rollback.

Phase 1 — Inventory & Lineage
	1.	Create reports/FOODS_LINEAGE.md with:
	•	List of all matched tables/views, row counts, last updated timestamps.
	•	Classification: source/raw, compat/normalization, canonical, published, scratch.
	•	Current data flow diagram (ASCII is fine) showing how each contributes to foods_published/_prod/_preview.

Phase 2 — Global Data-Health Sweep

For each participating table/view:
	•	Detect and count stringified arrays/JSON in ingredients_tokens, available_countries, sources.
	•	Find invalid slugs (brand_slug, name_slug) not matching [a-z0-9_-].
	•	Find duplicate product_key clusters.
	•	Compute field coverage snapshot: form, life_stage, kcal_per_100g, ingredients_tokens, price_per_kg_eur, price_bucket.
	•	Output reports/FOODS_HEALTH_BEFORE.md with a per-table summary and global totals.

Phase 3 — Normalization & Fixes (consistent across ALL tables)
	•	Type repair: convert stringified arrays → true arrays/JSON (propagate through compat/canonical so published reads correct types).
	•	Slug sanitization: normalize *_slug to [a-z0-9_-] (strip commas and exotic punctuation).
	•	Duplicate resolver: consolidate by cluster with deterministic rule (prefer richer nutrition → newer timestamp → source priority). Keep a provenance record of winners/losers.
	•	Brand normalization: apply the brand-phrase map and family mapping uniformly across all tables so brand_slug is consistent (Royal Canin, Hill’s, Purina families, etc.).
	•	Safe inference (optional): fill life_stage from high-confidence name patterns only where missing; record provenance.

Produce:
	•	reports/FIXPACK_V2_TYPES.md (counts fixed by table, sample BEFORE→AFTER)
	•	reports/FIXPACK_V2_SLUGS.md (invalid → fixed examples)
	•	reports/FIXPACK_V2_DEDUP.md (clusters, keep/drop rationale)
	•	reports/FIXPACK_V2_BRANDS.md (normalization deltas & family grouping)

Phase 4 — Pipeline Recompose & Environment Views
	•	Rebuild/refresh the pipeline explicitly:
foods_union_all (union of all normalized sources) → foods_canonical (deduped, scored) → foods_published_preview and foods_published_prod (prod uses allowlist join).
	•	Ensure the allowlist join is applied to foods_published_prod.
	•	Refresh brand quality MVs for both environments.

Deliver:
	•	reports/FOODS_PIPELINE_AFTER.md (row counts per layer; preview vs prod brand & row counts)
	•	reports/FOODS_COMPARE_PREVIEW_PROD_AFTER.md (delta vs before)

Phase 5 — Brand Spotlights & RC Reconciliation
	•	Run a brand spotlight sweep (top 20 by SKU): coverage, outliers, and missing fields per brand.
	•	Royal Canin: scan every source/compat table for RC variants; if present anywhere, show exact table & counts and ensure they surface in foods_union_all. If absent, add to NEW_BRANDS_QUEUE.md (Tier-1) with seed sources.

Output:
	•	reports/FOODS_BRAND_SPOTLIGHT.md (top 20 brands snapshot)
	•	reports/ROYAL_CANIN_RECONCILE_V2.md (found & linked vs queued to harvest)

Phase 6 — Acceptance Gates & Rollback
	•	Rerun global health metrics; produce reports/FOODS_HEALTH_AFTER.md.
	•	Success criteria:
	•	Stringified arrays = 0 outstanding across all pipeline layers.
	•	Invalid slugs = 0 outstanding.
	•	Duplicate product_key clusters reduced with clear winners recorded.
	•	Preview/prod both build cleanly; brand & row counts reported.
	•	Provide reports/FIXPACK_V2_ROLLBACK.md with SQL to revert snapshots if needed.