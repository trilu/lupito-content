> **Before you stsart:** READ AADF.md (/Users/sergiubiris/Desktop/lupito-content/AADF.md)
  
**MILESTONE 1**

> **Goal:** add AADF as a second source, run a 30-URL seed, and merge into foods_published so Admin can use it immediately.


> **Tasks**

1. > Create profiles/aadf_profile.yaml (mode: html, rate_limit_ms: 2000, jitter ±300ms) with selectors for:
    
    - > brand, product name
        
    - > composition/ingredients (raw text)
        
    - > analytical table: Protein, Fat/Oil, Fibre, Ash, Moisture (regex + table fallback)
        
    - > energy (kcal/100g or kJ/kg → normalize to kcal/100g)
        
    - > life stage, form (infer from page labels)
        
    - > optional rating
        
    
2. > Add jobs/aadf_scrape.py mirroring the pfx job (seed-list only for now):
    
    - > Save raw HTML → gs://lupito-content-raw-eu/aadf/YYYY-MM-DD/<hash>.html
        
    - > Parse + normalize (decimal commas, “oil & fat” → fat; Atwater estimate when energy missing)
        
    - > Upsert food_raw (raw_type='html') and food_candidates (fingerprint = md5(brand+name+ingredients))
        
    - > Harvest report: scanned/new/updated/skipped/errors
        
    
3. > **Dedup preference:** if the same brand+normalized name exists from multiple sources, keep both rows in food_candidates but in foods_published **prefer the row with kcal present**. Implement via:
    
    - > New view logic: group by (brand_slug, name_slug) and pick the row with kcal_per_100g IS NOT NULL first; otherwise any.
        
    - > Add source_domain to the published view so we can see which won.
        
    
4. > Create seed/aadf_urls.txt (ask me if you need a few starter URLs), run:

python jobs/aadf_scrape.py --seed-list seed/aadf_urls.txt --limit 30

4. > Then export a QA CSV (20 rows: brand, name, protein%, fat%, kcal/100g, contains_chicken).
    
5. > Verify:
    
    - > SELECT COUNT(*) FROM foods_published; increases.
        
    - > Admin → Brand Alternatives (staging, EU fallback ON) shows items; some now include **grams/day** (kcal known).
        
    

## **Why parallel (vs. later)**

- It’s isolated (new profile + job); won’t break PFX.
    
- It fills your biggest gap (macros/kcal) immediately, improving **match scores** and enabling **grams/day** in Admin.
    
- You can keep PFX running for breadth (price/packs), while AADF supplies nutrition depth.


**MILESTONE 2**

## **Prompt — “Unify sources, prefer kcal (AADF > others), keep PFX price”**

Goal
Create a single published view that deduplicates products coming from multiple sources and picks the “best” row per product:
- Prefer rows with kcal_per_100g present.
- If tie, prefer rows with protein & fat present.
- If still tie, prefer AADF (allaboutdogfood.co.uk) over petfoodexpert.com, then any other.
- As final tie-breaker, use last_seen_at DESC (most recent).
- Keep price info (EUR, price_per_kg) from whichever row has it (often PFX), but keep nutrition (kcal/protein/fat) from the “best” row.

Deliverables
1) A SQL file at /db/merge_foods_view.sql that:
   - Adds helper slugs (computed in view): brand_slug, name_slug.
   - Defines a product_key = lower(brand_slug || '|' || name_slug || '|' || coalesce(form,'any')).
   - Computes a score for each row:
       kcal_present*100 + protein_present*10 + fat_present*10
       + CASE source_domain WHEN 'allaboutdogfood.co.uk' THEN 5 WHEN 'petfoodexpert.com' THEN 3 ELSE 0 END
   - Uses ROW_NUMBER() OVER (PARTITION BY product_key ORDER BY score DESC, last_seen_at DESC) to pick the top row as “primary”.
   - Builds a view foods_published_unified AS:
        • All standard columns we expose today (id, source_domain, source_url, brand, product_name AS name, form, life_stage,
          kcal_per_100g, protein_percent, fat_percent, fiber_percent, ash_percent, moisture_percent,
          ingredients_tokens, contains_chicken, available_countries,
          price_eur, price_per_kg, price_bucket, gtin, quality_rating, first_seen_at, last_seen_at).
        • price_eur / price_per_kg / price_bucket should be taken from the “best available among the group”
          (COALESCE with MIN() or MAX() across the group) while nutrition comes from the primary row.
        • Add columns: brand_slug, name_slug, product_key, and a jsonb “sources” array that lists contributing rows
          (id + source_domain + has_kcal bool) for debugging.
   - CREATE OR REPLACE VIEW foods_published points to foods_published_unified (so the AI service doesn’t need changes).
   - Uses only CREATE OR REPLACE VIEW and ALTER TABLE IF NOT EXISTS where needed. Do NOT drop tables.

2) Apply guide section at bottom of the SQL file as comments:
   -- How to run in Supabase SQL editor
   -- How to rollback: CREATE OR REPLACE VIEW foods_published AS SELECT * FROM food_candidates; (if ever needed)

3) A quick verification script /db/verify_merge.sql printed after the main SQL:
   - Count groups: SELECT count(*) FROM (SELECT DISTINCT product_key FROM foods_published) t;
   - How many rows have kcal now vs null:
       SELECT
         sum((kcal_per_100g IS NOT NULL)::int) AS with_kcal,
         sum((kcal_per_100g IS NULL)::int)  AS no_kcal,
         count(*) AS total
       FROM foods_published;
   - Sample 10 merged rows with their sources jsonb.

Assumptions
- Source domains appear in food_candidates.source_domain (e.g., 'allaboutdogfood.co.uk', 'petfoodexpert.com').
- product_name column in food_candidates holds the human name; brand holds brand.
- If your exact column names differ, adapt accordingly.

Extra polish (nice-to-have)
- If pack_sizes are available in food_candidates, compute price_per_kg when possible; otherwise keep whatever you already compute in the existing view.
- Keep available_countries default ['EU'] when null.

Acceptance
- View compiles in Supabase without dropping data.
- SELECT * FROM foods_published LIMIT 5 returns unified rows.
- Nutrition columns often come from AADF (when present); prices often come from PFX (when present).
- The verification queries show that with_kcal increased (vs previous view).