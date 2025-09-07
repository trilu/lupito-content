-- ============================================================================
-- MILESTONE 3: Swap foods_published to Unified View
-- ============================================================================
-- This script replaces the current foods_published view with the new unified
-- version that combines and deduplicates data from all sources.
--
-- IMPORTANT: This will affect any services using the foods_published view!
-- Make sure to test thoroughly before running in production.
-- ============================================================================

-- ============================================================================
-- STEP 1: BACKUP CURRENT VIEW DEFINITION
-- ============================================================================
-- Store the current view definition for rollback if needed
-- You can get the current definition with:
-- SELECT pg_get_viewdef('foods_published', true);

-- ============================================================================
-- ROLLBACK INSTRUCTIONS (IF NEEDED)
-- ============================================================================
-- To rollback to the previous foods_published view, run:
/*
CREATE OR REPLACE VIEW foods_published AS
SELECT 
  id,
  source_domain,
  source_url,
  brand,
  product_name,
  form,
  life_stage,
  kcal_per_100g,
  protein_percent,
  fat_percent,
  fiber_percent,
  ash_percent,
  moisture_percent,
  ingredients_raw,
  -- Ensure tokens are trimmed and lowercased
  ARRAY(
    SELECT DISTINCT LOWER(TRIM(token))
    FROM UNNEST(ingredients_tokens) AS token
    WHERE TRIM(token) != ''
  ) AS ingredients_tokens,
  -- Ensure contains_chicken is set based on tokens
  CASE 
    WHEN contains_chicken = TRUE THEN TRUE
    WHEN EXISTS (
      SELECT 1 
      FROM UNNEST(ingredients_tokens) AS token 
      WHERE LOWER(token) IN ('chicken', 'chicken fat', 'chicken meal', 'chicken liver')
    ) THEN TRUE
    ELSE FALSE
  END AS contains_chicken,
  pack_sizes,
  price_eur,
  -- Derive price bucket based on price_eur
  CASE
    WHEN price_eur IS NULL THEN 'mid'
    WHEN price_eur < 3 THEN 'low'
    WHEN price_eur < 6 THEN 'mid'
    ELSE 'high'
  END AS price_bucket,
  -- Ensure available_countries defaults to EU
  COALESCE(available_countries, '{EU}') AS available_countries,
  gtin,
  first_seen_at,
  last_seen_at,
  -- Additional derived fields for completeness checks
  CASE
    WHEN kcal_per_100g IS NOT NULL 
     AND protein_percent IS NOT NULL 
     AND fat_percent IS NOT NULL 
    THEN TRUE
    ELSE FALSE
  END AS has_complete_nutrition,
  -- Add nutrition calculation notes
  CASE
    WHEN kcal_basis = 'estimated' THEN 'Calories estimated from protein/fat/fiber'
    WHEN kcal_basis = 'as_fed' THEN 'Calories as fed basis'
    WHEN kcal_basis = 'dry_matter' THEN 'Calories dry matter basis'
    ELSE NULL
  END AS nutrition_note
FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;
*/

-- ============================================================================
-- STEP 2: PERFORM THE SWAP
-- ============================================================================

-- Drop the existing view
DROP VIEW IF EXISTS foods_published CASCADE;

-- Create the new view pointing to the unified data
CREATE OR REPLACE VIEW foods_published AS
SELECT 
    -- Core identity fields
    id,
    brand,
    name as product_name,  -- Map 'name' back to 'product_name' for compatibility
    
    -- Product characteristics
    form,
    life_stage,
    
    -- Ingredients
    ingredients_tokens,
    contains_chicken,
    NULL::TEXT as ingredients_raw,  -- Not preserved in unified view
    
    -- Nutrition
    kcal_per_100g,
    protein_percent,
    fat_percent,
    NULL::NUMERIC as fiber_percent,    -- Not in canonical schema
    NULL::NUMERIC as ash_percent,      -- Not in canonical schema
    NULL::NUMERIC as moisture_percent, -- Not in canonical schema
    
    -- Pricing
    price_per_kg,
    price_bucket,
    NULL::NUMERIC as price_eur,  -- Original EUR price not preserved
    NULL::TEXT[] as pack_sizes,  -- Not preserved in unified view
    
    -- Availability
    available_countries,
    
    -- Media
    image_public_url,
    image_public_url as image_url,  -- Alias for compatibility
    
    -- Metadata
    source_domain,
    NULL::TEXT as source_url,  -- Not preserved in unified view
    NULL::TEXT as gtin,        -- Not preserved in unified view
    first_seen_at,
    last_seen_at,
    
    -- Additional unified fields (new capabilities)
    brand_slug,
    name_slug,
    product_key,
    quality_score,
    sources,
    
    -- Derived compatibility fields
    CASE
        WHEN kcal_per_100g IS NOT NULL 
         AND protein_percent IS NOT NULL 
         AND fat_percent IS NOT NULL 
        THEN TRUE
        ELSE FALSE
    END AS has_complete_nutrition,
    
    'Unified from multiple sources'::TEXT as nutrition_note,
    
    -- Extra fields for backward compatibility
    NULL::TEXT as fingerprint,
    NULL::TEXT as kcal_basis
    
FROM foods_published_unified;

-- Grant appropriate permissions (adjust as needed)
GRANT SELECT ON foods_published TO authenticated;
GRANT SELECT ON foods_published TO anon;
GRANT SELECT ON foods_published TO service_role;

-- ============================================================================
-- STEP 3: VERIFICATION QUERIES
-- ============================================================================

-- Check total count
SELECT COUNT(*) as total_products FROM foods_published;

-- Check price bucket distribution
SELECT price_bucket, COUNT(*) as count 
FROM foods_published 
GROUP BY price_bucket 
ORDER BY price_bucket;

-- Check nutrition data coverage
SELECT 
    SUM((kcal_per_100g IS NOT NULL)::int) as have_kcal,
    SUM((kcal_per_100g IS NULL)::int) as no_kcal,
    ROUND(100.0 * SUM((kcal_per_100g IS NOT NULL)::int) / COUNT(*), 1) as kcal_coverage_percent
FROM foods_published;

-- Check form distribution
SELECT form, COUNT(*) as count 
FROM foods_published 
GROUP BY form 
ORDER BY COUNT(*) DESC;

-- Check life_stage distribution
SELECT life_stage, COUNT(*) as count 
FROM foods_published 
GROUP BY life_stage 
ORDER BY COUNT(*) DESC;

-- Check products with multiple sources
SELECT 
    COUNT(*) as total,
    SUM((jsonb_array_length(sources) > 1)::int) as multi_source,
    ROUND(100.0 * SUM((jsonb_array_length(sources) > 1)::int) / COUNT(*), 1) as multi_source_percent
FROM foods_published;

-- Sample unified products
SELECT 
    brand,
    product_name,
    form,
    life_stage,
    price_bucket,
    has_complete_nutrition,
    jsonb_array_length(sources) as source_count
FROM foods_published
WHERE jsonb_array_length(sources) > 1
LIMIT 5;

-- ============================================================================
-- IMPORTANT POST-SWAP CHECKS
-- ============================================================================
/*
After running this swap, verify:

1. Any applications using foods_published still work correctly
2. API endpoints return expected data
3. Search functionality works as expected
4. No performance degradation

If issues occur, use the rollback SQL above to restore the previous view.
*/

-- ============================================================================
-- OPTIONAL: CREATE MATERIALIZED VIEW FOR PERFORMANCE
-- ============================================================================
/*
If the view is too slow, consider creating a materialized view:

CREATE MATERIALIZED VIEW foods_published_mat AS
SELECT * FROM foods_published;

CREATE INDEX idx_foods_mat_brand ON foods_published_mat(brand);
CREATE INDEX idx_foods_mat_form ON foods_published_mat(form);
CREATE INDEX idx_foods_mat_life_stage ON foods_published_mat(life_stage);
CREATE INDEX idx_foods_mat_price_bucket ON foods_published_mat(price_bucket);
CREATE INDEX idx_foods_mat_product_key ON foods_published_mat(product_key);
CREATE INDEX idx_foods_mat_ingredients_gin ON foods_published_mat USING gin(ingredients_tokens);

-- Refresh periodically with:
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_published_mat;
*/