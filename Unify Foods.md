MILESTONE 1

**Prompt:**

Create db/foods_compat.sql that:

- Defines **two compatibility views** projecting each source into the **canonical schema** from the mapping doc:
    
    - food_candidates_compat
        
    - food_brands_compat
        
    
- For each, produce columns the AI needs:
    
    id, brand, name, form, life_stage, ingredients_tokens, contains_chicken, kcal_per_100g, protein_percent, fat_percent, price_per_kg, price_bucket, available_countries, image_public_url, first_seen_at, last_seen_at, source_domain.
    
- Apply the **normalizers and derivations** exactly as in the doc (form/life_stage normalization, tokenization fallback, contains_chicken from tokens, price_bucket from price_per_kg if missing, default countries = ['EU']). 
    
- Include quick sanity queries at the bottom (as comments): select count(*) from food_candidates_compat; and select count(*) from food_brands_compat;.
    

**Acceptance:** both views compile and return rows.

MILESTONE 2

**Prompt:**

Create db/foods_published_unified.sql that:

- Builds a union foods_union_all of the two compat views.
    
- Adds brand_slug, name_slug, product_key = lower(brand_slug || '|' || name_slug || '|' || coalesce(form,'any')).
    
- Scores each row (deterministic “best row” rules):
    
    - +100 if kcal_per_100g present
        
    - +10 if protein_percent present
        
    - +10 if fat_percent present
        
    - +5 if source_domain='allaboutdogfood.co.uk', +3 if 'petfoodexpert.com', +0 otherwise
        
    
- Uses row_number() over (partition by product_key order by score desc, last_seen_at desc) to pick the **primary** row.
    
- Creates **foods_published_unified** with:
    
    - **Nutrition from the primary row**,
        
    - **Price fields by coalescing across the group** (so PFX pricing survives when nutrition comes from AADF/brands),
        
    - available_countries default ['EU'],
        
    - a sources jsonb array listing contributing rows (id, domain, has_kcal).
        
    
- Adds helpful indexes (bucket, kcal, GIN on ingredients_tokens) at the end.
    

  

**Acceptance:** select count(*) from foods_published_unified; returns ~the size of your logical catalog; bucket distribution looks sane.

MILESTONE 3

**Prompt:**

Create db/swap_foods_published.sql that:

- Does CREATE OR REPLACE VIEW foods_published AS SELECT * FROM foods_published_unified;
    
- Includes a **rollback** comment (how to restore previous definition).
    
- Prints quick checks (as comments):

select count(*) total from foods_published;
select price_bucket, count(*) from foods_published group by 1 order by 1;
select sum((kcal_per_100g is not null)::int) have_kcal,
       sum((kcal_per_100g is null)::int)  no_kcal
from foods_published;