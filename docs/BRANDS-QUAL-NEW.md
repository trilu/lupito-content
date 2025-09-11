Prompt A — Content repo (Manufacturer Enrichment Sprint)

Goal
Enrich the catalog using manufacturer websites for our ~200+ brands, focusing on form, life_stage, kcal_per_100g, ingredients_tokens, and price_per_kg_eur. All changes go to preview first (foods_published_preview).

A) Targeting & prep
	1.	Build a brand → official website map for all brands (use our brand_slug + light web lookup); store it as data/brand_sites.yaml (domain, country, notes, robots stance).
	2.	Rank brands by impact score = SKU count × (100 – completion%). Start with top 20.

B) Crawl plan (feed-first, then HTML)
	•	Try to find feeds/CSV/JSON; if none, crawl product pages with strict robots compliance and rate limits (existing jitter).
	•	Save raw HTML snapshots to our GCS bucket (same convention as petfood jobs).

C) Extraction & normalize
	•	Prefer structured data (JSON-LD / microdata). Otherwise, CSS/XPath per brand profile.
	•	Extract: brand, product_name, pack_size, price(+currency), form, life_stage, ingredients (raw text), protein/fat/fibre/moisture, kcal (if present).
	•	Normalize to our canonical schema; tokenize ingredients; compute price_per_kg_eur from price + pack size; derive kcal via Atwater only when missing.
	•	Never change brand_slug. Use our brand truth map.

D) Match & merge (preview only)
	•	Matching key: brand_slug + normalized_name_base + pack_weight_grams (+ GTIN/EAN if present).
	•	Keep a match confidence (0–1).
	•	Auto-merge only when ≥0.9 confidence and only fill missing/clearly inferior fields. Everything else goes to a manual review CSV.
	•	Preserve provenance in sources array and timestamps.

E) Gates & reports
	•	Acceptance gates per brand (on preview):
	•	form ≥ 95%, life_stage ≥ 95%, valid kcal (200–600) ≥ 90%, ingredients_tokens ≥ 85%, price_per_kg_eur ≥ 70%, zero malformed arrays.
	•	Produce:
	•	MANUF_SOURCES.md (site list + robots/licensing notes)
	•	MANUF_DELTA.md (before→after per brand + global)
	•	MANUF_OUTLIERS.md (kcal/price sanity)
	•	MANUF_PROMOTE_PROPOSALS.md (SQL to promote brands that pass)

F) Constraints
	•	Respect robots; skip blocked sites.
	•	Batch work (e.g., 20 brands per run).
	•	No row caps in analysis; paginate fetches.
	•	Keep arrays as jsonb, never stringified.
	•	Don’t touch production views or AI/Admin repos.

Deliverables
	1.	data/brand_sites.yaml, top-20 run complete with raw snapshots in GCS.
	2.	Updated foods_published_preview with coverage deltas.
	3.	Promotion proposals for brands that pass all gates.

⸻

Prompt B — Content repo (Retailer Feed Intake “Handshake”)

Goal
Prepare to ingest retailer data dumps (CSV/JSON/XLSX) that we will supply, to fill missing form, life_stage, kcal_per_100g, ingredients_tokens, price_per_kg_eur.

A) Intake contract
	•	Create docs/RETAILER_FEED_SPEC.md specifying the minimal columns retailers should provide:
	•	brand, product_name, gtin/ean (optional but ideal), pack_size (with unit), unit_price + currency, ingredients_text, protein_percent, fat_percent, fibre_percent, moisture_percent, kcal_per_100g (if available), product_url, image_url.
	•	Provide a mapping template (templates/retailer_mapping.csv) so we can map any vendor column names → our canonical fields.

B) Staging & adapters
	•	Add staging tables: retailer_import_raw and retailer_import_norm.
	•	Build adapters for 2 formats: CSV and JSON (schema-agnostic using the mapping template).
	•	Normalize units (g/kg, kcal/100g), tokenize ingredients, compute price_per_kg_eur.

C) Match & merge preview
	•	Use same match key & confidence scoring as manufacturer flow.
	•	Merge rules: Manufacturer > Retailer. Retailer can fill missing fields and price_per_kg_eur.
	•	Produce merge preview (counts, examples, conflict reasons).

D) Reports & gates
	•	RETAILER_DELTA.md (coverage uplift), RETAILER_OUTLIERS.md (sanity checks).
	•	Only propose promotions (SQL) for brands that meet gates on preview.

Constraints
	•	Don’t auto-promote; keep changes in preview.
	•	Preserve provenance.
	•	Keep arrays proper jsonb.
	•	No substring brand detection—use brand_slug mapping only.