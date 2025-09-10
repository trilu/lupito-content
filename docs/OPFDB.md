Objective: Ingest Open Pet Food Facts as a new enrichment source and lift coverage for ingredients/allergens, kcal/macros, form & life_stage, and images. Keep it read-additive; publish through foods_published_v2 and swap only after gates pass.

https://world.openpetfoodfacts.org/data

⸻

0) Guardrails & licensing
	•	Use bulk dumps (not page scraping). Source: OPFF data page (MongoDB dump) and data-fields reference. Keep the exact dump URL + SHA in the report.
	•	Respect ODbL: store provenance (source: "OPFF", dump date, URL, field-level origin), and add an attribution note for OPFF in our reports.
	•	No production table changes; all work in staging/enrichment tables; atomic swap after acceptance.

⸻

1) Import & normalize
	1.	Fetch the latest OPFF dump; record fetched_at, URL, sha256.
	2.	Load into opff_raw (JSON per product).
	3.	Build opff_compat view/table mapping key fields to our canonical names (one row per product):
	•	barcode (primary key if present), brand, product_name, quantity (parse), categories_tags, labels_tags,
	•	ingredients_text (+ language), ingredients_tags, ingredients_analysis_tags,
	•	nutriments.energy-kcal_100g → kcal_per_100g, plus macros if present (protein/fat/fiber/ash/moisture),
	•	primary image URL(s).
	4.	Derive form and life_stage from categories_tags / labels_tags / name regex (dry|wet|freeze_dried|raw; puppy|adult|senior|all).
	5.	Tokenize ingredients_text → ingredients_tokens; generate allergen_groups using our mapping (chicken/beef/fish_salmon/grain_gluten/etc.).

⸻

2) Enrichment tables
	•	Create foods_enrichment_opff with only high-confidence fields we want to import:
kcal_per_100g, macros, form, life_stage, ingredients_tokens, allergen_groups, ingredients_unknown=false when tokens exist, images.
	•	Each column must have field-level provenance {source:"OPFF", method:"dump", fetched_at: <date>, confidence: 0.7–0.95}.

⸻

3) Reconcile (v2)
	•	Update foods_published_v2 precedence to include OPFF:
overrides > enrichment_prices_v2 > enrichment_classify_v2 > enrichment_allergens > **enrichment_opff** > original_source > default.
	•	Keep ingredients_unknown strictly boolean.
	•	Indexes: (product_key), (brand_slug), (form), (life_stage).

⸻

4) Reports (put under /reports/OPFF/)
	1.	OPFF_IMPORT.md: dump date, file size, row count, % dog vs cat vs other (via categories), language split for ingredients, and field coverage we can use.
	2.	OPFF_COVERAGE_DELTA.md: before→after lift on our foods_published for:
	•	kcal_per_100g, macros
	•	ingredients_tokens, allergen_groups
	•	form, life_stage
	•	images presence
	3.	Conflicts sample (100 products): where OPFF conflicts with an existing source (kcal, form, life_stage). Show which source wins (via *_from).
	4.	Brand impact: Top-20 brands improved most by OPFF (new kcal, new tokens, new form/life_stage).
	5.	Attribution note included (ODbL + link).

⸻

5) Acceptance gates to include OPFF in production
	•	kcal_per_100g coverage +≥5 pp lift (and 0 new outliers).
	•	ingredients_tokens + allergen_groups +≥15 pp lift on the catalog.
	•	form and life_stage +≥15 pp lift (or to ≥80% if already higher).
	•	No degradation in existing fields (conflict rate ≤2%).
	•	If passed, update foods_published → point to v2, keep _prev for rollback.