Objective: Drive breed data quality to “A+” (≥98% coverage for operational fields; zero critical outliers), using our existing Wikipedia scraper plus 1–2 backup sources. Keep API contracts stable.

⸻

0) Guardrails & Scope
	•	Do not break existing view names used by AI/Admin. Build new views/tables with _v2 suffixes and swap atomically only after QA passes.
	•	Respect robots.txt and rate limits for all external sources. Cache raw HTML/JSON in GCS.
	•	Provenance is mandatory: every enriched value must record source, fetched_at, confidence.

⸻

1) Target Fields & Coverage Goals (A+)

We care about two layers of data:
	1.	Operational (used by AI math):
	•	size_category ∈ {xs,s,m,l,xl} — 100%
	•	growth_end_months, senior_start_months — 100% (defaults allowed, marked)
	•	adult_weight_min_kg, adult_weight_max_kg, adult_weight_avg_kg — ≥95%
	2.	Editorial (for traits/cards/tips):
	•	height_min_cm, height_max_cm — ≥95%
	•	lifespan_min_years, lifespan_max_years, lifespan_avg_years — ≥90%
	•	Narrative snippets (if present): keep, but not required for A+

Add quality flags on publish:
	•	size_from ∈ {override,enrichment,source,default}
	•	age_bounds_from ∈ {override,enrichment,source,default}
	•	weight_from, height_from, lifespan_from with same vocabulary
	•	conflict_flags (array) when sources disagree beyond thresholds

⸻

2) Multi-Source Enrichment Plan

Primary: Wikipedia (we already have the scraper).
Backups (low volume, only for misses or conflicts): FCI, AKC, The Kennel Club (UK). Use structured pages or reliable infoboxes.

Extraction rules:
	•	Parse male/female ranges where available; compute min/max and avg (rounded to 1 decimal).
	•	Normalize all units (kg/cm).
	•	Derive size_category from adult_weight_avg_kg using these bands (can be overridden by table overrides):
	•	xs < 5; s 5–10; m 10–25; l 25–45; xl > 45
	•	If weight missing but height present, derive temporary size from height:
	•	xs < 28 cm; s 28–38; m 38–53; l 53–63; xl > 63 cm (as fallback only)

Precedence logic (final value per field):
overrides > enrichment(primary=Wikipedia) > enrichment(backup sources) > original_source > default
Always write provenance: {source, fetched_at, method, confidence}.

⸻

3) Data Model Changes (build, don’t break)
	•	Create/refresh:
	•	breeds_overrides (manual hotfixes; include at least the breeds we know were wrong, e.g., labrador-retriever size = l).
	•	breeds_enrichment (one row per breed_slug with weight/height/lifespan + provenance, per-field).
	•	breeds_published_v2 (reconciled view): resolves each field by precedence above, emits *_from flags + conflict_flags.
	•	Add indexes: breeds_enrichment(breed_slug), breeds_published_v2(breed_slug). Ensure breed_slug unique.
	•	Do not swap breeds_published yet.

⸻

4) Quality Gates & Validation

Implement validation checks during build and publish:
	•	Numeric sanity
	•	adult_weight_min_kg >= 1 and <= 100
	•	adult_weight_max_kg >= adult_weight_min_kg
	•	height_min_cm >= 10 and <= 110; height_max_cm >= height_min_cm
	•	lifespan_min_years >= 5 and <= 20; lifespan_max_years >= lifespan_min_years
	•	Consistency
	•	If size_category=xs, then adult_weight_avg_kg < 5 (±1 kg tolerance) else flag conflict_flags += ["size_weight_mismatch"].
	•	Similar tolerances for s/m/l/xl thresholds.
	•	Defaults labeling
	•	If a field comes from a default (size from height; age bounds from size defaults), tag *_from="default" and include which rule.

Output validation artifacts (save under /reports):
	•	BREEDS_QUALITY_BEFORE.md (snapshot of current coverage)
	•	BREEDS_ENRICHMENT_RUN.md (counts per source, success/miss/error)
	•	BREEDS_CONFLICTS.csv (one row per breed with disagreements, with winning source and reason)
	•	BREEDS_QUALITY_AFTER.md (coverage %, outliers found/fixed, remaining gaps)
	•	BREEDS_SAMPLE_50.csv (50-row sample of the final publish view with all *_from flags)

⸻

5) Acceptance Criteria (must hit all)
	•	Coverage:
	•	size_category 100%
	•	growth_end_months & senior_start_months 100% (defaults allowed, labeled)
	•	≥95% for weight and height; ≥90% lifespan
	•	Zero critical outliers (none outside sanity bounds).
	•	≤1% of breeds with any conflict_flags.
	•	breeds_published_v2 query in < 50 ms for single breed (indexed).
	•	Reports saved to /reports folder with clear before/after metrics.

⸻

6) Deliverables & Swap
	1.	Paste BREEDS_QUALITY_BEFORE.md summary.
	2.	Run enrichment (Wikipedia first; use backups only for misses/conflicts).
	3.	Paste BREEDS_ENRICHMENT_RUN.md with counts: fetched, parsed, enriched, conflicts, fallbacks used.
	4.	Build breeds_published_v2 and paste BREEDS_QUALITY_AFTER.md + top 20 BREEDS_CONFLICTS.csv rows inline.
	5.	If all Acceptance Criteria pass, atomically swap breeds_published → point to the v2 reconciled view.
	6.	Final paste:
	•	Totals per field with coverage %
	•	of overridden breeds (from breeds_overrides)
	•	of enrichment wins (Wikipedia vs backups vs defaults)
	•	A 10-row sample (breed_slug, size_category, size_from, adult_weight_avg_kg, growth/senior months).

⸻

7) (Optional) Keep It Fresh
	•	Create a tiny weekly job that re-checks 5 random breeds and re-scrapes only if fetched_at > 180 days or if conflict_flags present; append to a rolling BREEDS_SPOTCHECK.md.