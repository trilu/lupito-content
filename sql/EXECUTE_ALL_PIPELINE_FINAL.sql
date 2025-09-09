-- ============================================================================
-- LUPITO CATALOG PIPELINE - COMPLETE EXECUTION SCRIPT (FINAL)
-- Run this in Supabase SQL Editor to create the complete pipeline
-- ============================================================================

-- ============================================================================
-- STEP 0: Clean up existing views/tables
-- ============================================================================

DROP VIEW IF EXISTS foods_published CASCADE;
DROP TABLE IF EXISTS foods_canonical CASCADE;
DROP VIEW IF EXISTS foods_union_all CASCADE;
DROP VIEW IF EXISTS food_candidates_compat CASCADE;
DROP VIEW IF EXISTS food_candidates_sc_compat CASCADE;
DROP VIEW IF EXISTS food_brands_compat CASCADE;

-- ============================================================================
-- STEP C1: Create Compatibility Views
-- ============================================================================

-- 1. food_candidates_compat
CREATE VIEW food_candidates_compat AS
SELECT 
    -- Product key
    LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
    LOWER(REPLACE(TRIM(product_name), ' ', '_')) || '|' || 
    COALESCE(form, 'unknown') as product_key,
    
    -- Core fields
    brand,
    LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
    product_name,
    LOWER(REPLACE(TRIM(product_name), ' ', '_')) as name_slug,
    form,
    
    -- Life stage normalization
    CASE 
        WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
        WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
        WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
        WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
        WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
        WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
        WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
        WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
        ELSE life_stage
    END as life_stage,
    
    -- Nutrition
    kcal_per_100g,
    CASE 
        WHEN kcal_per_100g IS NOT NULL THEN false
        WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN true
        ELSE false
    END as kcal_is_estimated,
    
    -- Calculate Atwater estimate if needed
    CASE 
        WHEN kcal_per_100g IS NOT NULL THEN kcal_per_100g
        WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN
            (protein_percent * 3.5) + (fat_percent * 8.5) + 
            ((100 - protein_percent - fat_percent - COALESCE(fiber_percent, 0) - 
              COALESCE(ash_percent::numeric, 8) - COALESCE(moisture_percent::numeric, 10)) * 3.5)
        ELSE NULL
    END as kcal_per_100g_final,
    
    protein_percent,
    fat_percent,
    
    -- Ingredients (convert to JSONB)
    to_jsonb(ingredients_tokens) as ingredients_tokens,
    
    -- Derive primary protein from tokens
    CASE
        WHEN ingredients_tokens::text ~* 'chicken' THEN 'chicken'
        WHEN ingredients_tokens::text ~* 'beef' THEN 'beef'
        WHEN ingredients_tokens::text ~* 'lamb' THEN 'lamb'
        WHEN ingredients_tokens::text ~* 'salmon' THEN 'salmon'
        WHEN ingredients_tokens::text ~* 'fish' THEN 'fish'
        WHEN ingredients_tokens::text ~* 'turkey' THEN 'turkey'
        WHEN ingredients_tokens::text ~* 'duck' THEN 'duck'
        ELSE NULL
    END as primary_protein,
    
    contains_chicken as has_chicken,
    ingredients_tokens::text ~* 'poultry' as has_poultry,
    
    -- Availability (convert to JSONB)
    to_jsonb(available_countries) as available_countries,
    
    -- Price
    price_eur as price_per_kg,
    CASE 
        WHEN price_eur <= 3.5 THEN 'Low'
        WHEN price_eur > 3.5 AND price_eur <= 7.0 THEN 'Mid'
        WHEN price_eur > 7.0 THEN 'High'
        ELSE NULL
    END as price_bucket,
    
    -- Metadata
    image_url,
    source_url as product_url,
    'food_candidates' as source,
    last_seen_at as updated_at,
    
    -- Quality score
    (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN kcal_per_100g IS NOT NULL OR 
              (protein_percent IS NOT NULL AND fat_percent IS NOT NULL) THEN 1 ELSE 0 END +
     CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN price_eur IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END -
     CASE WHEN kcal_per_100g IS NULL AND protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN 1 ELSE 0 END
    ) as quality_score
    
FROM food_candidates;

-- 2. food_candidates_sc_compat
CREATE VIEW food_candidates_sc_compat AS
SELECT 
    -- Product key
    LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
    LOWER(REPLACE(TRIM(product_name), ' ', '_')) || '|' || 
    COALESCE(form, 'unknown') as product_key,
    
    -- Core fields
    brand,
    LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
    product_name,
    LOWER(REPLACE(TRIM(product_name), ' ', '_')) as name_slug,
    form,
    
    -- Life stage normalization
    CASE 
        WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
        WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
        WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
        WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
        WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
        WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
        WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
        WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
        ELSE life_stage
    END as life_stage,
    
    -- Nutrition
    kcal_per_100g,
    CASE 
        WHEN kcal_per_100g IS NOT NULL THEN false
        WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN true
        ELSE false
    END as kcal_is_estimated,
    
    -- Calculate Atwater estimate if needed
    CASE 
        WHEN kcal_per_100g IS NOT NULL THEN kcal_per_100g
        WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN
            (protein_percent * 3.5) + (fat_percent * 8.5) + 
            ((100 - protein_percent - fat_percent - COALESCE(fiber_percent, 0) - 
              COALESCE(ash_percent::numeric, 8) - COALESCE(moisture_percent::numeric, 10)) * 3.5)
        ELSE NULL
    END as kcal_per_100g_final,
    
    protein_percent,
    fat_percent,
    
    -- Ingredients (convert text[] to jsonb)
    COALESCE(to_jsonb(ingredients_tokens), '[]'::jsonb) as ingredients_tokens,
    
    -- Derive primary protein from tokens
    CASE
        WHEN ingredients_tokens::text ~* 'chicken' THEN 'chicken'
        WHEN ingredients_tokens::text ~* 'beef' THEN 'beef'
        WHEN ingredients_tokens::text ~* 'lamb' THEN 'lamb'
        WHEN ingredients_tokens::text ~* 'salmon' THEN 'salmon'
        WHEN ingredients_tokens::text ~* 'fish' THEN 'fish'
        WHEN ingredients_tokens::text ~* 'turkey' THEN 'turkey'
        WHEN ingredients_tokens::text ~* 'duck' THEN 'duck'
        ELSE NULL
    END as primary_protein,
    
    COALESCE(contains_chicken, false) as has_chicken,
    COALESCE(ingredients_tokens::text ~* 'poultry', false) as has_poultry,
    
    -- Availability (convert to JSONB)
    to_jsonb(available_countries) as available_countries,
    
    -- Price (using retailer_price_eur)
    retailer_price_eur as price_per_kg,
    CASE 
        WHEN retailer_price_eur <= 3.5 THEN 'Low'
        WHEN retailer_price_eur > 3.5 AND retailer_price_eur <= 7.0 THEN 'Mid'
        WHEN retailer_price_eur > 7.0 THEN 'High'
        ELSE NULL
    END as price_bucket,
    
    -- Metadata
    image_url,
    retailer_url as product_url,  -- Using retailer_url instead of source_url
    'food_candidates_sc' as source,
    COALESCE(updated_at, last_scraped_at, created_at) as updated_at,
    
    -- Quality score
    (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN kcal_per_100g IS NOT NULL OR 
              (protein_percent IS NOT NULL AND fat_percent IS NOT NULL) THEN 1 ELSE 0 END +
     CASE WHEN ingredients_tokens IS NOT NULL AND jsonb_array_length(to_jsonb(ingredients_tokens)) > 0 THEN 1 ELSE 0 END +
     CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN retailer_price_eur IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END -
     CASE WHEN kcal_per_100g IS NULL AND protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN 1 ELSE 0 END
    ) as quality_score
    
FROM food_candidates_sc;

-- 3. food_brands_compat
CREATE VIEW food_brands_compat AS
SELECT 
    -- Product key (using brand_name and product_name columns)
    LOWER(REPLACE(TRIM(COALESCE(brand_name, manufacturer, '')), ' ', '_')) || '|' || 
    LOWER(REPLACE(TRIM(product_name), ' ', '_')) || '|' || 
    COALESCE(product_type, 'unknown') as product_key,
    
    -- Core fields
    COALESCE(brand_name, manufacturer, '') as brand,
    LOWER(REPLACE(TRIM(COALESCE(brand_name, manufacturer, '')), ' ', '_')) as brand_slug,
    product_name,
    LOWER(REPLACE(TRIM(product_name), ' ', '_')) as name_slug,
    product_type as form,
    
    -- Life stage normalization
    CASE 
        WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
        WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
        WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
        WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
        WHEN life_stage = 'puppy and adult' THEN 'all'
        WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
        WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
        WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
        WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
        ELSE life_stage
    END as life_stage,
    
    -- Nutrition (limited data available)
    NULL::numeric as kcal_per_100g,
    false as kcal_is_estimated,
    -- Try to estimate if we have protein and fat
    CASE 
        WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN
            (protein_percent * 3.5) + (fat_percent * 8.5) + 
            ((100 - protein_percent - fat_percent - COALESCE(fiber_percent, 0) - 15) * 3.5)
        ELSE NULL
    END as kcal_per_100g_final,
    
    protein_percent,
    fat_percent,
    
    -- Ingredients (handle main_ingredients - could be text or text[])
    COALESCE(to_jsonb(main_ingredients), '[]'::jsonb) as ingredients_tokens,
    
    -- Derive primary protein
    CASE
        WHEN main_ingredients::text ~* 'chicken' THEN 'chicken'
        WHEN main_ingredients::text ~* 'beef' THEN 'beef'
        WHEN main_ingredients::text ~* 'lamb' THEN 'lamb'
        WHEN main_ingredients::text ~* 'salmon' THEN 'salmon'
        WHEN main_ingredients::text ~* 'fish' THEN 'fish'
        WHEN main_ingredients::text ~* 'turkey' THEN 'turkey'
        WHEN main_ingredients::text ~* 'duck' THEN 'duck'
        ELSE NULL
    END as primary_protein,
    
    COALESCE(main_ingredients::text ~* 'chicken', false) as has_chicken,
    COALESCE(main_ingredients::text ~* 'poultry', false) as has_poultry,
    
    -- Availability (use country_of_origin or default to EU)
    CASE 
        WHEN country_of_origin IS NOT NULL THEN 
            jsonb_build_array(country_of_origin)
        ELSE '["EU"]'::jsonb
    END as available_countries,
    
    -- Price (not available)
    NULL::numeric as price_per_kg,
    NULL as price_bucket,
    
    -- Metadata
    NULL as image_url,
    NULL as product_url,
    'food_brands' as source,
    created_at as updated_at,
    
    -- Quality score
    (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN main_ingredients IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN product_type IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END
    ) as quality_score
    
FROM food_brands;

-- ============================================================================
-- STEP C2: Union and Canonical Table
-- ============================================================================

-- Create union view
CREATE VIEW foods_union_all AS
SELECT * FROM food_candidates_compat
UNION ALL
SELECT * FROM food_candidates_sc_compat
UNION ALL
SELECT * FROM food_brands_compat;

-- Create canonical table with deduplication
CREATE TABLE foods_canonical AS
WITH ranked_products AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_key
            ORDER BY 
                -- 1. kcal known > estimated > null
                CASE 
                    WHEN kcal_per_100g_final IS NOT NULL AND NOT kcal_is_estimated THEN 1
                    WHEN kcal_per_100g_final IS NOT NULL AND kcal_is_estimated THEN 2
                    ELSE 3
                END,
                -- 2. specific life_stage > all > null
                CASE 
                    WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1
                    WHEN life_stage = 'all' THEN 2
                    ELSE 3
                END,
                -- 3. richer ingredients (more tokens)
                CASE 
                    WHEN ingredients_tokens IS NOT NULL THEN 
                        jsonb_array_length(ingredients_tokens)
                    ELSE 0
                END DESC,
                -- 4. price present > missing
                CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 2 END,
                -- 5. higher quality score
                quality_score DESC,
                -- 6. newest updated_at
                updated_at DESC NULLS LAST
        ) as rank,
        
        -- Track sources for provenance
        jsonb_build_object(
            'source', source,
            'updated_at', updated_at
        ) as source_info
    FROM foods_union_all
),
aggregated_sources AS (
    SELECT 
        product_key,
        jsonb_agg(source_info ORDER BY rank) as sources
    FROM ranked_products
    GROUP BY product_key
)
SELECT 
    r.product_key,
    r.brand,
    r.brand_slug,
    r.product_name,
    r.name_slug,
    r.form,
    r.life_stage,
    r.kcal_per_100g,
    r.kcal_is_estimated,
    r.kcal_per_100g_final,
    r.protein_percent,
    r.fat_percent,
    r.ingredients_tokens,
    r.primary_protein,
    r.has_chicken,
    r.has_poultry,
    r.available_countries,
    r.price_per_kg,
    r.price_bucket,
    r.image_url,
    r.product_url,
    r.source,
    r.updated_at,
    r.quality_score,
    a.sources
FROM ranked_products r
JOIN aggregated_sources a ON r.product_key = a.product_key
WHERE r.rank = 1;

-- Add indexes
CREATE UNIQUE INDEX idx_foods_canonical_product_key ON foods_canonical(product_key);
CREATE INDEX idx_foods_canonical_brand_slug ON foods_canonical(brand_slug);
CREATE INDEX idx_foods_canonical_life_stage ON foods_canonical(life_stage);
CREATE INDEX idx_foods_canonical_form ON foods_canonical(form);

-- ============================================================================
-- STEP C3: Published View and Additional Indexes
-- ============================================================================

-- Create foods_published view for AI consumption
CREATE VIEW foods_published AS
SELECT 
    product_key,
    brand,
    brand_slug,
    product_name,
    name_slug,
    form,
    life_stage,
    kcal_per_100g_final as kcal_per_100g,
    kcal_is_estimated,
    protein_percent,
    fat_percent,
    ingredients_tokens,
    primary_protein,
    has_chicken,
    has_poultry,
    available_countries,
    price_per_kg,
    price_bucket,
    image_url,
    product_url,
    source,
    updated_at,
    quality_score,
    sources
FROM foods_canonical;

-- Create GIN indexes for array/jsonb columns
CREATE INDEX IF NOT EXISTS idx_foods_canonical_countries_gin 
ON foods_canonical USING GIN (available_countries);

CREATE INDEX IF NOT EXISTS idx_foods_canonical_tokens_gin 
ON foods_canonical USING GIN (ingredients_tokens);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check row counts
SELECT 
    'food_candidates_compat' as table_name, COUNT(*) as row_count 
FROM food_candidates_compat
UNION ALL
SELECT 'food_candidates_sc_compat', COUNT(*) FROM food_candidates_sc_compat
UNION ALL
SELECT 'food_brands_compat', COUNT(*) FROM food_brands_compat
UNION ALL
SELECT 'foods_union_all', COUNT(*) FROM foods_union_all
UNION ALL
SELECT 'foods_canonical', COUNT(*) FROM foods_canonical
UNION ALL
SELECT 'foods_published', COUNT(*) FROM foods_published
ORDER BY table_name;

-- Check coverage metrics
SELECT 
    COUNT(*) as total_products,
    ROUND(100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*), 1) as life_stage_pct,
    ROUND(100.0 * COUNT(CASE WHEN kcal_per_100g_final IS NOT NULL THEN 1 END) / COUNT(*), 1) as kcal_pct,
    ROUND(100.0 * COUNT(CASE WHEN jsonb_array_length(ingredients_tokens) > 0 THEN 1 END) / COUNT(*), 1) as tokens_pct,
    ROUND(100.0 * COUNT(CASE WHEN price_per_kg IS NOT NULL THEN 1 END) / COUNT(*), 1) as price_pct
FROM foods_canonical;

-- Sample data
SELECT 
    brand,
    LEFT(product_name, 40) as product_name,
    form,
    life_stage,
    kcal_per_100g_final,
    primary_protein,
    has_chicken,
    price_bucket
FROM foods_canonical
LIMIT 10;