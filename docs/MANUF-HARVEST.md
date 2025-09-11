Run a real manufacturer enrichment (not simulation) for the current top-impact brands (from your impact queue): brit, burns, briantos. For each brand:
	•	Crawl only the manufacturer’s site & PDFs (respect robots; use existing rate limits).
	•	Extract:
	•	ingredients_raw (full text), plus a best-effort ingredients_language.
	•	Label macros: protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent (as-fed).
	•	kcal_per_100g (if present; if only kcal/kg, convert).
	•	life_stage and form from label/spec (reuse your rules).
	•	Set provenance fields (ingredients_source, macros_source, kcal_source = label|pdf|site), and store source URLs in sources.
	•	Upsert into the canonical write table by stable key (e.g., product_key or brand+slug), without touching price.
	•	Produce /reports/MANUF_ENRICH_RUN_YYYYMMDD.md with before→after coverage lifts for these brands:
	•	% with non-empty ingredients_tokens
	•	% with protein_percent & fat_percent
	•	% with kcal_per_100g
	•	Count of products updated, skipped, new.
If a brand site blocks scraping, pause and list what you need (e.g., proxy, API, manual CSV).