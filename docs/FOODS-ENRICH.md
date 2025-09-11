Objective: Lift the food catalog to “A+ felt quality” by enriching three fields at scale—allergen_groups, form/life_stage, and price/price_bucket—without breaking current APIs. Work in read-additive mode: build new tables/views, then swap atomically after QA.

⸻

0) Guardrails
	•	Do not modify production tables in place. Create _enrich tables and a foods_published_v2 reconciled view; only swap foods_published → v2 after acceptance gates pass.
	•	Respect robots.txt and apply low rate limits; cache raw pages/PDF/JSON in GCS with provenance.
	•	Every enriched field must include provenance {source, fetched_at, method, confidence} and a *_from ∈ {override,enrichment,source,default} flag.

⸻

1) Scope & Priorities
	•	Target set: Top 1,000 SKUs by brand + availability (or the Top-50 brands by product count), then widen.
	•	Fields to enrich now:
	1.	allergen_groups (derived from ingredients_tokens)
	2.	form (dry|wet|freeze_dried|raw) and life_stage (puppy|adult|senior|all)
	3.	price_eur, price_per_kg_eur, price_bucket (low|mid|high)

⸻

2) Allergen Groups (from tokens)
	•	Create token → allergen group mapping table allergen_map with synonyms (case-insensitive, stemmed). Start with these groups:
	•	chicken (chicken, poultry, poultry meal, chicken meal)
	•	beef (beef, bovine)
	•	fish_salmon (salmon, trout, whitefish, tuna, fish meal, fish oil)
	•	lamb (lamb, ovine)
	•	turkey, duck, pork
	•	egg, dairy (milk, whey, casein)
	•	grain_gluten (wheat, barley, rye, oats, cereals, gluten)
	•	corn_maize (corn, maize)
	•	soy (soya, soy protein)
	•	pea_legume (pea, lentil, chickpea, legume)
	•	potato, rice
	•	novel_protein (venison, rabbit, kangaroo, insect, buffalo, goat)
	•	Build foods_enrichment_allergens that, for each product, derives unique allergen_groups based on ingredients_tokens.
	•	Set ingredients_unknown=false when tokens exist; otherwise true. Keep provenance (mapping:v1).

Outputs:
	•	/reports/FOODS_ALLERGEN_COVERAGE.md (coverage % per group; before/after chart)
	•	/sql/enrichment/allergen_map.sql + the SELECT used to populate foods_enrichment_allergens

⸻

3) Form & Life-Stage (NLP + rules)
	•	Create foods_enrichment_classify that derives:
	•	form using name+brand cues (regex/NLP): dry|wet|freeze_dried|raw (synonyms: “kibble/pellet”→dry; “pouch/can/gravy”→wet; “freeze-dried/air-dried”→freeze_dried).
	•	life_stage from name/label: “puppy/junior/growth”→puppy; “adult/maintenance”→adult; “senior/mature/7+”→senior; “all life stages”→all.
	•	Apply a small brand rule list for edge cases (e.g., brand lines that always mean a form).
	•	Include provenance like {source:"nlp_rules_v1", confidence: 0.7–0.95}.

Outputs:
	•	/reports/FOODS_CLASSIFY_COVERAGE.md (coverage before/after for form & life_stage; mismatch counts where name says puppy but field ≠ puppy)
	•	/sql/enrichment/classify_rules.sql

⸻

4) JSON-LD Pricing (and buckets)
	•	For each target product URL (manufacturer or retailer page you already snapshot):
	•	Parse JSON-LD Product/Offer for price, priceCurrency, weight/size if present. Normalize to EUR and compute price_per_kg_eur.
	•	If missing, fall back to a brand-level RRP table (create brand_rrp with form-specific medians).
	•	Derive price_bucket with thresholds (draft; adjust after distribution):
	•	low: < 15 EUR/kg, mid: 15–30, high: > 30
	•	Store in foods_enrichment_prices with provenance (jsonld, rrp_estimate), and a bucket_from flag.

Outputs:
	•	/reports/FOODS_PRICING_COVERAGE.md (price fields coverage, per-kg distribution, bucket shares)
	•	/sql/enrichment/pricing_jsonld.sql

⸻

5) Reconcile & Publish (v2)
	•	Build foods_published_v2 with precedence:
overrides > enrichment_prices > enrichment_classify > enrichment_allergens > original_source > default
	•	Emit for each enriched field: *_from and provenance. Ensure ingredients_unknown is boolean.
	•	Add indexes: (product_key), (brand_slug), (form), (life_stage), (price_bucket).

Outputs:
	•	/sql/enrichment/foods_published_v2.sql

⸻

6) Quality Gates & Acceptance

Recompute coverage and write /reports/FOODS_QUALITY_AFTER.md. Swap only if all pass:
	•	allergen_groups coverage ≥ 85% (overall; plus per-brand table for Top-50)
	•	form coverage ≥ 95%, life_stage ≥ 95%
	•	price_bucket coverage ≥ 70%, with ≥ 50% of rows having real price_per_kg_eur
	•	Zero critical outliers (kcal absurdities; bogus price)
	•	conflict_flags ≤ 2% of total rows

If passed, atomically swap: point foods_published to v2; keep _prev for rollback.

⸻

7) Deliverables to paste back
	1.	The Executive Summary (from FOODS_QUALITY_AFTER.md): before/after coverage for allergens, form/life_stage, price, plus 5-line next steps.
	2.	Top-15 brands by improvement in allergen coverage and price coverage.
	3.	A FOODS_TOP50_IMPACT.csv (brand, products, allergen_cov_before→after, price_bucket_before→after, notes).
	4.	Confirmation that foods_published was swapped (or reasons it was not).