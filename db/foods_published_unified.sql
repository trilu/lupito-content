-- ============================================================================
-- MILESTONE 2: Unified Foods View with Deduplication
-- ============================================================================
-- This script creates a unified view that:
-- 1. Unions both compatibility views
-- 2. Adds slug fields for deduplication
-- 3. Scores rows to pick the best data source
-- 4. Deduplicates by product_key (brand|name|form)
-- 5. Preserves pricing data across sources
-- 6. Creates indexes for performance
-- ============================================================================

-- Drop existing objects if they exist
DROP VIEW IF EXISTS foods_published_unified CASCADE;
DROP VIEW IF EXISTS foods_union_all CASCADE;

-- ============================================================================
-- HELPER FUNCTIONS FOR SLUGIFICATION
-- ============================================================================

-- Create slug from text (lowercase, alphanumeric, spaces to hyphens)
CREATE OR REPLACE FUNCTION create_slug(input TEXT) RETURNS TEXT AS $$
BEGIN
    IF input IS NULL THEN
        RETURN 'unknown';
    END IF;
    
    -- Convert to lowercase, replace non-alphanumeric with spaces, then spaces with hyphens
    RETURN LOWER(
        TRIM(
            regexp_replace(
                regexp_replace(input, '[^a-zA-Z0-9\s]', ' ', 'g'),
                '\s+', '-', 'g'
            ),
            '-'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- STEP 1: UNION ALL COMPATIBLE VIEWS
-- ============================================================================
CREATE VIEW foods_union_all AS
SELECT * FROM food_candidates_compat
UNION ALL
SELECT * FROM food_brands_compat;

-- ============================================================================
-- STEP 2: CREATE UNIFIED VIEW WITH DEDUPLICATION
-- ============================================================================
CREATE VIEW foods_published_unified AS
WITH scored_products AS (
    -- Add slugs and scoring to all rows
    SELECT 
        *,
        create_slug(brand) as brand_slug,
        create_slug(name) as name_slug,
        LOWER(
            create_slug(brand) || '|' || 
            create_slug(name) || '|' || 
            COALESCE(form, 'any')
        ) as product_key,
        
        -- Calculate score for row selection (higher is better)
        (
            -- Nutrition data quality scores
            CASE WHEN kcal_per_100g IS NOT NULL THEN 100 ELSE 0 END +
            CASE WHEN protein_percent IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN fat_percent IS NOT NULL THEN 10 ELSE 0 END +
            
            -- Source reliability scores
            CASE 
                WHEN source_domain = 'allaboutdogfood.co.uk' THEN 5
                WHEN source_domain = 'petfoodexpert.com' THEN 3
                ELSE 0
            END +
            
            -- Bonus for having ingredients
            CASE WHEN array_length(ingredients_tokens, 1) > 0 THEN 5 ELSE 0 END +
            
            -- Bonus for having image
            CASE WHEN image_public_url IS NOT NULL THEN 2 ELSE 0 END
        ) as quality_score
        
    FROM foods_union_all
),
ranked_products AS (
    -- Rank products within each product_key group
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY product_key 
            ORDER BY quality_score DESC, last_seen_at DESC
        ) as row_rank
    FROM scored_products
),
aggregated_data AS (
    -- Aggregate data across all rows for each product_key
    SELECT 
        product_key,
        
        -- Collect all source information
        jsonb_agg(
            jsonb_build_object(
                'id', id,
                'domain', source_domain,
                'has_kcal', (kcal_per_100g IS NOT NULL),
                'has_protein', (protein_percent IS NOT NULL),
                'has_price', (price_per_kg IS NOT NULL),
                'score', quality_score
            ) ORDER BY quality_score DESC
        ) as sources,
        
        -- Aggregate pricing data (take first non-null)
        (ARRAY_AGG(price_per_kg ORDER BY 
            CASE WHEN price_per_kg IS NOT NULL THEN 0 ELSE 1 END,
            quality_score DESC
        ) FILTER (WHERE price_per_kg IS NOT NULL))[1] as best_price_per_kg,
        
        (ARRAY_AGG(price_bucket ORDER BY 
            CASE WHEN price_per_kg IS NOT NULL THEN 0 ELSE 1 END,
            quality_score DESC
        ))[1] as best_price_bucket,
        
        -- Aggregate image URLs (take first non-null)
        (ARRAY_AGG(image_public_url ORDER BY 
            CASE WHEN image_public_url IS NOT NULL THEN 0 ELSE 1 END,
            quality_score DESC
        ) FILTER (WHERE image_public_url IS NOT NULL))[1] as best_image_url,
        
        -- Aggregate countries (union of all)
        ARRAY(
            SELECT DISTINCT unnest(available_countries)
            FROM ranked_products rp2
            WHERE rp2.product_key = ranked_products.product_key
        ) as all_countries
        
    FROM ranked_products
    GROUP BY product_key
)
-- Final selection: primary row with aggregated fields
SELECT 
    -- Core fields from the best row
    rp.id,
    rp.brand,
    rp.name,
    rp.form,
    rp.life_stage,
    
    -- Ingredients from the best row
    rp.ingredients_tokens,
    rp.contains_chicken,
    
    -- Nutrition from the best row (most complete data)
    rp.kcal_per_100g,
    rp.protein_percent,
    rp.fat_percent,
    
    -- Pricing: coalesce from all sources
    COALESCE(rp.price_per_kg, ad.best_price_per_kg) as price_per_kg,
    COALESCE(
        CASE 
            WHEN rp.price_per_kg IS NOT NULL THEN rp.price_bucket
            ELSE NULL
        END,
        ad.best_price_bucket,
        'mid'
    ) as price_bucket,
    
    -- Countries: union of all sources or default
    COALESCE(
        NULLIF(ad.all_countries, '{}'),
        ARRAY['EU']::TEXT[]
    ) as available_countries,
    
    -- Image: from best source
    COALESCE(rp.image_public_url, ad.best_image_url) as image_public_url,
    
    -- Metadata
    rp.first_seen_at,
    rp.last_seen_at,
    rp.source_domain,
    
    -- Additional unified fields
    rp.brand_slug,
    rp.name_slug,
    rp.product_key,
    rp.quality_score,
    ad.sources
    
FROM ranked_products rp
JOIN aggregated_data ad ON rp.product_key = ad.product_key
WHERE rp.row_rank = 1;

-- ============================================================================
-- STEP 3: CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Create materialized view for better performance (optional)
-- CREATE MATERIALIZED VIEW foods_published_unified_mat AS 
-- SELECT * FROM foods_published_unified;

-- Create indexes on the materialized view if created
-- CREATE INDEX idx_foods_unified_bucket ON foods_published_unified_mat(price_bucket);
-- CREATE INDEX idx_foods_unified_kcal ON foods_published_unified_mat(kcal_per_100g);
-- CREATE INDEX idx_foods_unified_brand ON foods_published_unified_mat(brand);
-- CREATE INDEX idx_foods_unified_form ON foods_published_unified_mat(form);
-- CREATE INDEX idx_foods_unified_life_stage ON foods_published_unified_mat(life_stage);
-- CREATE INDEX idx_foods_unified_product_key ON foods_published_unified_mat(product_key);
-- CREATE INDEX idx_foods_unified_ingredients_gin ON foods_published_unified_mat USING gin(ingredients_tokens);

-- ============================================================================
-- SANITY CHECK QUERIES
-- ============================================================================

-- Total count - should be less than sum of both tables due to deduplication
-- SELECT COUNT(*) as total_unified_products FROM foods_published_unified;

-- Price bucket distribution
-- SELECT price_bucket, COUNT(*) as count 
-- FROM foods_published_unified 
-- GROUP BY price_bucket 
-- ORDER BY price_bucket;

-- Check nutrition data coverage
-- SELECT 
--     COUNT(*) as total,
--     SUM(CASE WHEN kcal_per_100g IS NOT NULL THEN 1 ELSE 0 END) as has_kcal,
--     SUM(CASE WHEN protein_percent IS NOT NULL THEN 1 ELSE 0 END) as has_protein,
--     SUM(CASE WHEN fat_percent IS NOT NULL THEN 1 ELSE 0 END) as has_fat,
--     SUM(CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 0 END) as has_price,
--     SUM(CASE WHEN image_public_url IS NOT NULL THEN 1 ELSE 0 END) as has_image
-- FROM foods_published_unified;

-- Check form distribution
-- SELECT form, COUNT(*) as count 
-- FROM foods_published_unified 
-- GROUP BY form 
-- ORDER BY COUNT(*) DESC;

-- Check life_stage distribution  
-- SELECT life_stage, COUNT(*) as count 
-- FROM foods_published_unified 
-- GROUP BY life_stage 
-- ORDER BY COUNT(*) DESC;

-- Sample products with multiple sources
-- SELECT brand, name, form, sources, quality_score
-- FROM foods_published_unified
-- WHERE jsonb_array_length(sources) > 1
-- LIMIT 10;

-- Check source domain distribution in primary rows
-- SELECT source_domain, COUNT(*) as count
-- FROM foods_published_unified
-- GROUP BY source_domain
-- ORDER BY COUNT(*) DESC;