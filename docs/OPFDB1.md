Objective: Upgrade OPFF integration from 0.3% to a useful match rate by implementing Matching v2 (brand aliases + fuzzy product matching + cross-language normalization). In parallel, enable an “add-new” import path when products don’t yet exist in our catalog. Read-additive only; no production swap until gates pass.

⸻

0) Guardrails
	•	Read-only against production tables; write to _stg / _enrich tables and opff_match_v2.
	•	Keep provenance and confidence on every matched field.
	•	Save all SQL under /sql/opff_match_v2/ and reports under /reports/OPFF_MATCH_V2/.

⸻

1) Quick brand overlap report (discover where matching is plausible)
	•	Produce OPFF_BRAND_OVERLAP.md & OPFF_BRAND_OVERLAP.csv with:
	1.	brand_slug frequency in foods_published (our catalog)
	2.	brand_slug frequency in opff_compat (OPFF) after normalization
	3.	Intersection: brands present in both (counts on both sides)
	•	Rank the Top 50 overlapping brands as the first matching target set.

⸻

2) Brand alias mapping (cross-language & variants)
	•	Create brand_aliases_opff with columns: alias, canonical_brand_slug, source (manual|auto), lang, confidence.
	•	Seed automatically from:
	•	Lowercased, punctuation-stripped brand names.
	•	Common variants (“Purina Pro Plan” vs “Pro Plan”; “Royal Canin” vs “RC”).
	•	Cross-language hints (fr/es/de): e.g., “au poulet” doesn’t change brand, but helps product tokenization.
	•	Output OPFF_BRAND_ALIAS_GAPS.csv listing top unmapped OPFF brands that appear in overlap but don’t map cleanly—so we can add 10–20 manual aliases in a minute.

⸻

3) Product name normalization & signatures
	•	Build a deterministic normalizer used on both sides (our catalog & OPFF):
	•	Lowercase; remove punctuation/stopwords; strip pack sizes (e.g., 12x85g, 2 kg), marketing fluff (“complete”, “premium”), and flavor adjectives that aren’t primary proteins.
	•	Extract primary tokens: brand (via alias map), main proteins (chicken/salmon/beef/lamb/etc.), form hints (dry/wet/freeze_dried/raw), life-stage hints (puppy/adult/senior/all), and line names (e.g., “Hypoallergenic”, “Sensitive Skin”).
	•	Persist a product signature per row: {brand_canonical, tokens_sorted, form_hint, lifestage_hint}.

⸻

4) Matching v2 candidates & scoring
	•	For each product in the overlap brand set:
	1.	Candidate pool = OPFF rows with same canonical_brand_slug.
	2.	Compute similarity:
	•	Token Jaccard over normalized tokens (name minus size),
	•	Char Fuzzy (~Levenshtein on the concatenated normalized name),
	•	Protein overlap (shared protein tokens),
	•	Form/Life-stage agreement (from hints).
	3.	Score = weighted sum (start with Token Jaccard 0.5, Protein 0.2, Char Fuzzy 0.2, Form/Life-stage 0.1).
	4.	Accept if: score ≥ 0.75; manual-review bucket if 0.60 ≤ score < 0.75; otherwise reject.
	•	Save matches to opff_match_v2 with: our_product_key, opff_id/barcode, score, signals(json), status ∈ {auto, needs_review, rejected}, created_at.

Deliverables:
	•	OPFF_MATCH_V2_SUMMARY.md: counts auto/needs_review/rejected; precision sample (see §6).
	•	OPFF_MATCH_V2_NEEDS_REVIEW.csv: top 200 borderline cases for quick human confirm.

⸻

5) Enrichment from matched OPFF rows
	•	For status=auto (and any human-approved): write to foods_enrichment_opff_v2 only the high-value fields we want:
	•	ingredients_tokens (+ derive allergen_groups via our existing map),
	•	kcal_per_100g, macros (when sane),
	•	form, life_stage (only if confidence ≥0.8),
	•	images (primary image URL),
with field-level provenance {source:"OPFF", method:"match_v2", confidence, fetched_at}.
	•	Do not import pricing from OPFF (expected absent).

⸻

6) QA & precision check
	•	Randomly sample 100 auto-matches; generate a side-by-side CSV (OPFF_MATCH_V2_SAMPLE_100.csv) with: brand, product names, tokens, proteins, form/life_stage hints, image URLs.
	•	Report estimated precision ≥95% on auto-matches. If lower, adjust thresholds/weights and re-run.
	•	For needs_review, produce a compact HTML/CSV that the team can flip to “approve/reject” quickly (write decisions back to opff_match_v2).

⸻

7) Optional: “Add-new” path
	•	For OPFF products with no match but useful data (good tokens/kcal), insert into food_candidates_opff with a new product_key scheme (opff:<barcode or slug>), so Ops can consider onboarding them as new SKUs.
	•	Keep them isolated from production until approved; include a small Admin list if needed later.

⸻

8) Reconcile & gates
	•	Update foods_published_v2 precedence to include foods_enrichment_opff_v2 (after our own enrichment/overrides, before original source).
	•	Recompute coverage deltas vs baseline for: ingredients_tokens, allergen_groups, kcal_per_100g, form, life_stage.
	•	Acceptance to keep OPFF in v2:
	•	Match rate on overlap brands: ≥ 20% of their SKUs enriched (first pass target).
	•	Auto-match precision on sample: ≥ 95%.
	•	Coverage lifts: ingredients_tokens +≥10 pp, allergen_groups +≥10 pp, and either form +≥10 pp or life_stage +≥10 pp.
	•	0 new kcal outliers introduced.
	•	If not met, keep OPFF in standalone tables and retry.

⸻

9) Reports to paste back
	•	/reports/OPFF_MATCH_V2/OPFF_BRAND_OVERLAP.md (with CSV).
	•	/reports/OPFF_MATCH_V2/OPFF_MATCH_V2_SUMMARY.md (auto/needs_review/rejected, precision result).
	•	/reports/OPFF_MATCH_V2/OPFF_COVERAGE_DELTA_AFTER.md (field coverage lifts).
	•	A 50-row sample CSV of enriched products showing product_key, brand, product_name, ingredients_tokens, allergen_groups, kcal_per_100g, form, life_stage, *_from, provenance.