Goal: Heal all “split-brand” cases (multi-word brand broken across brand and product_name), standardize brand slugs, fix names, and rebuild keys/deduping. Make it idempotent and guarded (dry-run + QA before applying).

What to build (no code pasted back; implement end-to-end):
	1.	Discovery & Evidence (dry-run first)
	•	Scan foods catalog for rows where:
	•	brand is a short token (≤6 chars or in a known set), and
	•	product_name begins with a capitalized token (or two) that, when concatenated with brand, forms a frequent pair across ≥10 SKUs.
Example: brand='Royal' + product_name starts 'Canin …' → candidate 'Royal Canin'.
	•	Also detect hyphen/apostrophe variants and common subbrand starters:
	•	e.g., “Hill’s” / “Hills”; “Purina Pro Plan”, “Purina ONE”; “Farmina N&D”, “Taste of the Wild”, “Nature’s Variety Instinct”, etc.
	•	Produce reports/BRAND_SPLIT_CANDIDATES.md with:
	•	Top candidate pairs, counts, examples (product_key, brand, product_name)
	•	Confidence score per pair (frequency × consistency)
	•	Suspected false positives (e.g., “Canine …” vs “Canin …”, different word)
	•	Do not mutate data yet.
	2.	Canonical brand phrase map
	•	Create/extend brand_aliases (or a new brand_phrase_map) with columns:
source_brand, prefix_from_name, canonical_brand, strip_prefix_regex, confidence, notes.
	•	Auto-populate from the discovery step (high-confidence suggestions) and add a curated seed list for common multi-word brands and lines:
	•	Examples to include:
	•	“Royal Canin”
	•	“Hill’s Science Plan”, “Hill’s Prescription Diet” (canonical brand = “Hill’s”, line = “Science Plan”/“Prescription Diet”)
	•	“Purina Pro Plan”, “Purina ONE” (canonical brand = “Purina”, line = “Pro Plan”/“ONE”)
	•	“Farmina N&D”, “Carnilove”, “Taste of the Wild”, “Nature’s Variety Instinct”, etc.
	•	Policy: canonicalize to the major brand (e.g., “purina”, “hills”, “royal_canin”), and extract an optional brand_line (e.g., “pro_plan”, “one”, “science_plan”) for later scoring.
	3.	Normalization rules (idempotent)
	•	When a row matches a phrase map entry:
	•	Set canonical brand and brand_slug (snake case).
	•	Remove the matched brand phrase (or trailing fragment) from the start of product_name only (word-boundary, case/space/hyphen tolerant).
	•	Also fix historic half-strips like leading “Canin ” (but guard against “Canine”).
	•	Extract optional brand_line from the removed phrase remainder (e.g., “Pro Plan”, “ONE”, “Science Plan”).
	•	Preserve original_full_name for provenance.
	•	Recompute name_slug and product_key = ${brand_slug}|${name_slug}|${form||'unknown'}.
	•	Run dedupe for all impacted clusters (same product_key after rebuild) and merge exact duplicates.
	•	Make transformations idempotent: running twice should produce no further changes.
	4.	Safeguards & False-positive guards
	•	Use word boundaries and exact phrase tokens to avoid stripping inside real words (e.g., don’t remove “Canin” from “Canine”).
	•	Don’t strip if product_name already looks cleaned (no leading brand fragment).
	•	Keep a denylist for tricky collisions discovered during the dry-run.
	5.	QA gates & regression checks
	•	Add sql/qa/BRAND_SPLIT_GUARDS.sql with checks that must pass before/after applying:
	•	No rows in published views where product_name starts with the second token of any multi-word brand (e.g., '^Canin\\b' while brand_slug='royal_canin').
	•	No published rows with brand_slug variants like ^royal(?!_canin), ^hills(?!$), ^purina_(?!one|pro_plan) unless intentionally modeled as line.
	•	Zero product_key collisions introduced (except merges logged).
	•	Write reports/BRAND_SPLIT_BEFORE.md and BRAND_SPLIT_AFTER.md with:
	•	Distinct brand_slug counts (before→after)
	•	Count of product_name starting with known split fragments (before→after)
	•	SKU counts & completion% for top affected brands (before→after)
	•	Number of deduped merges
	6.	Refresh & outputs
	•	Refresh canonical/published views + brand quality MVs.
	•	Update scoreboard and allowlist views.
	•	Confirm that search/recommendation queries over brands like “royal_canin”, “hills”, “purina” now show unified SKU sets.

Definition of Done
	•	All multi-word brands are canonicalized (single brand_slug).
	•	No product_name begins with orphaned brand fragments (“Canin ”, “Science Plan ”, “Pro Plan ”, etc.).
	•	product_key rebuilt on canonical slug; dedupe complete.
	•	QA guards pass; before/after reports attached.
	•	Changes are idempotent and covered by guard queries to prevent regressions on future harvests.

Nice-to-have (if quick)
	•	Add optional brand_line column in canonical/published views for subbrand scoring (“pro_plan”, “one”, “science_plan”, “prescription_diet”).
	•	Emit a small brand glossary (reports/BRAND_GLOSSARY.md) listing canonical brand → known lines.