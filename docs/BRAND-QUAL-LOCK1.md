Prompt A — Use the full catalog (no row caps)

Goal: Make sure we work on all ~5,151 rows, not the 1,000-row sample.
Do:
	1.	Inspect how foods_canonical is built or queried. Search the repo and SQL for any LIMIT 1000, .limit(1000), .range(0, 999), or pagination that stops at 1k.
	2.	Rebuild or rewire foods_canonical so it reflects the full, deduped union (previously ~5,151 rows). Print exact row counts for foods_union_all, foods_canonical, foods_published_preview, foods_published_prod.
	3.	Confirm arrays are jsonb (not strings) for ingredients_tokens, available_countries, sources. If not, fix in the canonical layer.
	4.	Produce a short “FULL-CATALOG-ON.md” with before/after row counts and the precise place where the 1k cap was removed.

⸻

Prompt B — Re-apply split-brand & brand_slug truth (on full data)

Goal: Canonicalize brands across the entire catalog using brand_slug only (no substring matching).
Do:
	1.	Run the split-brand detector across all rows in foods_canonical and the upstream sources used to build it.
	2.	Update the canonical brand mapping (e.g., Royal|Canin → royal_canin, Hill’s|Science Plan → hills, Purina|Pro Plan → purina_pro_plan, Taste|of the Wild → taste_of_the_wild, etc.).
	3.	Apply fixes only where brand_slug is wrong/empty; emit a delta report (id, old_brand_slug, new_brand_slug, reason).
	4.	Rebuild foods_canonical (or apply UPDATEs), don’t touch Prod yet. Print counts for big brands strictly by brand_slug (royal_canin, hills, purina, purina_one, purina_pro_plan, taste_of_the_wild).
	5.	Write “BRANDS-FULL-FIX.md” summarizing changes.

⸻

Prompt C — Re-run enrichment on Preview (form, life-stage, allergens, kcal, price)

Goal: Lift coverage to gates on the full catalog in Preview.
Do:
	1.	Re-run classification for form and life_stage using name + description + brand heuristics (multi-language). Report brand-level coverage deltas.
	2.	Re-apply allergen detection from ingredients_tokens.
	3.	Kcal sanity: keep only 200..600 as valid; flag outliers; propose fixes (re-parse or estimate from macros).
	4.	Price: extract pack size → compute price_per_kg_eur → derive price_bucket.
	5.	Refresh foods_published_preview and output PREVIEW-COVERAGE-REPORT.md with before/after metrics vs gates.

Gates (Preview):
	•	life_stage ≥ 95%
	•	form ≥ 90%
	•	ingredients coverage ≥ 85%
	•	kcal_valid (200..600) ≥ 90%
	•	kcal_outliers = 0

⸻

Prompt D — Recompute brand quality & shortlist promotions

Goal: See who’s ready to go ACTIVE.
Do:
	1.	Refresh foods_brand_quality_preview_mv.
	2.	Generate a Brand Scoreboard (Preview) sorted by sku_count and completion_pct.
	3.	Produce a PROMOTION-CANDIDATES.md listing brands that pass all gates. Include the exact SQL to update brand_allowlist to ACTIVE (but don’t execute).
	4.	Include a quick “What Prod will gain?” summary: SKUs added and adult/puppy/senior counts.

⸻

Prompt E — Promote the winners, verify Prod isn’t empty

Goal: Safely add more “Food-ready” SKUs to Prod.
Do:
	1.	Execute the approved allowlist updates from Prompt D (only the ones we green-light).
	2.	Refresh foods_published_prod and foods_brand_quality_prod_mv.
	3.	Output PROD-VERIFICATION.md with:
	•	brands, rows, and coverage now in Prod
	•	adult/puppy/senior dry counts
	•	confirmation that Prod remains non-empty

⸻

Prompt F — Big-brand probe (RC / Hill’s / Purina)

Goal: Confirm presence (or absence) by truth, not guesses.
Do:
	1.	Count rows in Preview strictly by brand_slug IN ('royal_canin','hills','purina','purina_one','purina_pro_plan','taste_of_the_wild').
	2.	If counts are still 0, explicitly state “Not harvested yet” and add them to the TOP HARVEST QUEUE with source suggestions.
	3.	If non-zero, list top 10 product names to prove they’re legit (not substring artifacts).

⸻

Prompt G — Tiny weekly loop (so this stays healthy)

Goal: Keep data quality high without manual babysitting.
Do:
	1.	Add a simple weekly task: refresh Preview enrichment, refresh MVs, rebuild Scoreboard, and emit a “WEEKLY-CATALOG-HEALTH.md” (1-pager).
	2.	If any ACTIVE brand in Prod falls below gates (e.g., bad re-harvest), flag it in the report (don’t auto-demote).