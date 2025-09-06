Create /profiles/pfx_profile.yaml with selectors for petfoodexpert product pages:

- brand selector
- product name selector
- ingredients selector (raw string)
- nutrition table rows: protein, fat, fiber, ash, moisture (%), energy (kcal/100g or kJ/100g)
- pack sizes & price blocks (amount + currency)
- GTIN/EAN if available
- Fallbacks if a field is absent; leave null rather than guess.

Implement /etl/normalize_foods.py helpers:
- parse_percent("25%") -> 25.0
- parse_energy(value, unit) -> kcal_per_100g; convert kJ to kcal (kcal = kJ / 4.184)
- estimate_kcal_from_analytical(protein,fat,carb_est):
    carb_est = 100 - (protein + fat + fiber + ash + moisture) but >=0
    kcal/100g ≈ 4*protein + 9*fat + 4*carb_est (note as estimate)
- tokenize_ingredients(raw) -> tokens (lower, split on punctuation, dedupe)
- contains(tokens, ["chicken","chicken fat","poultry"]) -> bool
- derive_form(name, category) -> 'dry'|'wet'|'raw'|'vet'
- derive_life_stage(name, tags) -> 'puppy'|'adult'|'senior'|'all'
- normalize_currency(price, currency) -> EUR (use a supplied static rate in config; annotate “converted_at” date)

Extend /jobs/pfx_scrape.py:
- Inputs:
  --from-sitemap OR --seed-list path
  --limit N
  --delay-ms 1500 default, jitter ±300ms
- Steps per URL:
  1) fetch with proper UA, respect robots, delay
  2) store raw in GCS: gs://<bucket>/petfoodexpert/<yyyy-mm-dd>/<hash>.html
  3) parse using profile & helpers -> parsed dict
  4) compute fingerprint; upsert into food_raw (update last_seen_at) and food_candidates (on change)
- Print a harvest report: scanned, new, updated, skipped, errors