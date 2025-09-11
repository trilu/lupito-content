Objective: Pass the food catalog quality gates by (1) boosting form and life_stage coverage to ≥95%, (2) getting price_bucket to ≥70% with ≥50% price_per_kg_eur, and (3) clearing kcal outliers. Work in read-additive mode and publish via a reconciled v2 view; do not swap production until acceptance passes.

⸻

0) Guardrails
	•	Read-additive only: create/update _enrichment tables and foods_published_v2; swap to production only after gates pass.
	•	Respect robots.txt & rate limits; cache raw JSON-LD/HTML/PDF in GCS with provenance.
	•	Every enriched field must include {source, fetched_at, method, confidence} and *_from ∈ {override,enrichment,source,default}.

⸻

1) Form & Life-stage — Classifier v2 (Priority #1)

Goal: Raise form and life_stage coverage from ~55% to ≥95%.
Plan:
	1.	Dictionary expansion (multi-lingual & brand lines):
	•	Form hints: “kibble”, “dry”, “pellet”, “cold pressed” → dry; “can”, “tin”, “pouch”, “paté”, “gravy”, “stew” → wet; “freeze-dried”, “air-dried” → freeze_dried; “raw”, “BARF” → raw.
	•	Life-stage hints: “puppy”, “junior”, “growth”; “adult”, “maintenance”; “senior”, “mature”, “7+”; “all life stages”, “complete for all ages”.
	•	Brand line overrides: build a small table mapping recurring line names to form/life_stage for top brands (use the Brand Quality Leaderboard to pick these).
	2.	Name + description pass: parse product_name and, where available, short/long description.
	3.	Heuristic backstops:
	•	Use kcal/100g and moisture when present: dry typically 320–450 kcal/100g & moisture ≤12%; wet 60–120 kcal/100g & moisture ≥70%.
	•	Packaging tokens: “24×400g”, “12×85g pouches” → wet bias; “12kg bag” → dry bias.
	4.	Confidence scoring: attach classification_confidence (0–1). If low (<0.6), leave null (we’ll improve later rather than inject noise).
	5.	Write results to foods_enrichment_classify_v2 with provenance nlp_rules_v2 and any brand override hits recorded.

Deliverables:
	•	/reports/FOODS_CLASSIFY_COVERAGE.md: before→after coverage for form & life_stage, mismatch counts (e.g., name contains “puppy” but life_stage≠puppy).
	•	/sql/enrichment/classify_rules_v2.sql (rules, not code dump—document patterns & precedence).

⸻

2) Pricing — price_per_kg + buckets (Priority #2)

Goal: Achieve ≥50% price_per_kg_eur and ≥70% price_bucket.
Plan:
	1.	Pack size parser: derive net weight (kg) from name/pack fields using robust patterns:
	•	single: (\d+(\.\d+)?)\s?(kg|g|ml) → convert to kg
	•	multipack: (\d+)\s?[x×]\s?(\d+(\.\d+)?)\s?(g|ml) → multiply & convert
	•	combos: choose the largest size when multiple matches appear in name & description.
	2.	JSON-LD Offer pass: for the target set, parse price, priceCurrency, weight/size if present; normalize to EUR, compute price_per_kg_eur.
	3.	Brand RRP fallback: create brand_rrp with per-form medians for top brands; fill price_per_kg_eur where JSON-LD is missing. Tag provenance (rrp_estimate).
	4.	Bucket thresholds (initial): low < 15 €/kg, mid 15–30, high > 30. Store bucket_from as jsonld|rrp_estimate|heuristic.
	5.	Write to foods_enrichment_prices_v2.

Deliverables:
	•	/reports/FOODS_PRICING_COVERAGE.md: coverage of price_per_kg_eur, bucket distribution, brand×form medians (top 50).
	•	/sql/enrichment/pricing_v2.sql (documented approach).

⸻

3) Kcal Outliers — detect & repair (Priority #3)

Goal: Reduce kcal outliers to 0 and keep kcal coverage ≥95%.
Plan:
	1.	Define form-specific sane ranges (dry 250–500; wet 40–150; freeze_dried 300–600; raw 120–300 kcal/100g).
	2.	For out-of-range SKUs:
	•	If macros present, re-estimate kcal via Atwater and replace with provenance kcal_from=estimate.
	•	Else clear kcal to null and tag kcal_flag="invalid_cleared".
	3.	Log all changes to foods_enrichment_kcal_fixes (product_key, old_kcal, new_kcal, method).

Deliverables:
	•	/reports/FOODS_KCAL_OUTLIERS_FIXES.md: counts fixed by method (estimated vs cleared), final outliers=0.

⸻

4) Reconcile & quality gates
	•	Build foods_published_v2 precedence:
overrides > enrichment_prices_v2 > enrichment_classify_v2 > enrichment_allergens (existing) > original_source > default.
	•	Ensure ingredients_unknown is boolean (never null).
	•	Indexes: (product_key), (brand_slug), (form), (life_stage), (price_bucket).

Acceptance to swap (must pass):
	•	form ≥ 95%, life_stage ≥ 95%
	•	price_bucket ≥ 70% and price_per_kg_eur ≥ 50%
	•	0 kcal outliers (post-repair)
	•	No more than 2% rows with any conflict_flags

Outputs to paste back:
	•	/reports/FOODS_QUALITY_AFTER.md (executive summary with before→after metrics)
	•	Top-15 brands by improvement (form/life_stage & pricing)
	•	A 50-row sample (FOODS_SAMPLE_50.csv) showing product_name, form, life_stage, price_per_kg_eur, price_bucket, and all *_from flags
	•	Swap status: swapped or not swapped (with reasons)