CONTEXT RESTORE (TL;DR)

What we already built
	•	Canonical catalog: foods_canonical (source of truth).
	•	Views:
	•	foods_published_prod → ACTIVE brands only (used by prod).
	•	foods_published_preview → ACTIVE+PENDING brands (used by staging/QA).
	•	Allowlist table: brand_allowlist with statuses: ACTIVE, PENDING, PAUSED, REMOVED.
	•	ACTIVE: briantos, bozita
	•	PENDING: brit, alpha, belcando
	•	Quality MVs: foods_brand_quality_prod_mv, foods_brand_quality_preview_mv (brand coverage metrics).
	•	Brand rules: “brand_slug is the only truth”; no substring matching (solved “Royal Canin” ≠ “canine” false positives).
	•	Ingredients schema expanded: added ingredients_raw, ingredients_source, ingredients_parsed_at, ingredients_language, fiber_percent, ash_percent, moisture_percent, macros_source, kcal_source.
	•	Arrays typed: ingredients_tokens, available_countries, sources are real JSONB (not strings).

Current data status (remember these)
	•	Prod view count: ~80 items (ACTIVE only).
	•	Preview view count: ~240 items (ACTIVE+PENDING).
	•	Coverage highlights (last confirmed):
	•	Bozita ingredients coverage improved from 0% → ~64% after manufacturer harvest & merge.
	•	Belcando ~35% ingredients (needs more), Briantos ~34%.
	•	Kcal coverage generally strong; price is intentionally de-prioritized for now.
	•	Royal Canin / Hill’s / Purina: not in our current catalog slice yet (they require a future harvest wave; don’t assume presence).

Manufacturer snapshot & parse pipeline
	•	GCS bucket: gs://lupito-content-raw-eu/manufacturers/
	•	Bozita: 59 snapshots (good)
	•	Belcando: 19 snapshots (good)
	•	Briantos: 2 snapshots (limited)
	•	B1A merge path: parse → stage → server-side merge into foods_canonical (idempotent; creates new rows when missing).
	•	We are not doing retailer scraping right now. Stay manufacturer-first. Price comes later via feeds/affiliates.

Guardrails (please respect)
	•	Do not fetch or print secrets.
	•	Do not modify Cloud Run or other cloud configs unless explicitly asked.
	•	Don’t re-invent foods_published_*; they already exist and are wired to allowlist.
	•	Keep changes small and sequential: 1–2 steps, then stop and report.

What we want now
	1.	Raise ingredients & life-stage coverage for the brands we already have (ACTIVE+PENDING), using manufacturer pages and PDFs we’ve captured (or add more snapshots for the same brands if needed).
	2.	Do not wander to new sources (e.g., Zooplus) unless I ask.
	3.	Keep “Food-ready” SKU count in prod view comfortably >50 while improving preview coverage.

Quick reality checks you can run (read-only)
	•	Count items per view:
	•	SELECT COUNT(*) FROM foods_published_prod;
	•	SELECT COUNT(*) FROM foods_published_preview;
	•	Brand coverage (preview/prod):
	•	SELECT * FROM foods_brand_quality_preview_mv ORDER BY completion_pct DESC;
	•	SELECT * FROM foods_brand_quality_prod_mv ORDER BY completion_pct DESC;
	•	Ingredients coverage for a brand (example):
    SELECT brand_slug,
       COUNT(*) AS skus,
       SUM(CASE WHEN jsonb_typeof(ingredients_tokens)='array' AND jsonb_array_length(ingredients_tokens)>0 THEN 1 END) AS with_ingredients
FROM foods_published_preview
WHERE brand_slug IN ('bozita','belcando','briantos')
GROUP BY 1;
Acceptance gates (what “good” looks like)
	•	Food-ready per brand: life_stage present, kcal_per_100g in 200–600, non-empty ingredients_tokens.
	•	Coverage targets (preview) before promotion to ACTIVE:
	•	form ≥ 95%, life_stage ≥ 95%, ingredients ≥ 85%, kcal outliers = 0.
	•	Price coverage can remain low for now.

⸻

Your very next step (please do only this, then stop):

TASK: “Confirm current coverage for bozita, belcando, briantos in foods_brand_quality_preview_mv and foods_brand_quality_prod_mv (no code changes). Print a short delta table and propose the single highest-leverage enrichment action for the next 60 minutes using existing manufacturer snapshots (e.g., improve Belcando selectors, parse PDFs, or expand Bozita). Then stop and report.”