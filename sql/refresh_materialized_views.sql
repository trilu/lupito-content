-- ============================================================================
-- REFRESH MATERIALIZED VIEWS FOR BRAND QUALITY METRICS
-- ============================================================================
-- Purpose: Refresh the stale materialized views to reflect recent data changes
-- Last MVs update: 2025-09-11 (stale)
-- Current date: 2025-09-12
-- ============================================================================

-- Set timeout for long-running operations
SET statement_timeout = '10min';

-- Show current state before refresh
SELECT 
    'BEFORE REFRESH' as status,
    schemaname,
    matviewname,
    last_refresh_time
FROM pg_catalog.pg_matviews 
WHERE matviewname IN ('foods_brand_quality_preview_mv', 'foods_brand_quality_prod_mv');

-- ============================================================================
-- REFRESH PREVIEW MATERIALIZED VIEW
-- ============================================================================
-- This view includes ACTIVE + PENDING brands
-- Used by staging/QA environments

\timing on
\echo 'Refreshing foods_brand_quality_preview_mv...'

REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;

\echo 'Preview MV refreshed successfully'

-- ============================================================================
-- REFRESH PRODUCTION MATERIALIZED VIEW  
-- ============================================================================
-- This view includes only ACTIVE brands
-- Used by production environment

\echo 'Refreshing foods_brand_quality_prod_mv...'

REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_prod_mv;

\echo 'Production MV refreshed successfully'

-- ============================================================================
-- VERIFY REFRESH RESULTS
-- ============================================================================

-- Check new metrics for our target brands
\echo 'Checking updated metrics for Bozita, Belcando, Briantos...'

SELECT 
    'PREVIEW' as view_type,
    brand_slug,
    sku_count,
    ROUND(ingredients_cov, 1) as ingredients_pct,
    ROUND(form_cov, 1) as form_pct,
    ROUND(life_stage_cov, 1) as life_stage_pct,
    ROUND(kcal_cov, 1) as kcal_pct,
    ROUND(completion_pct, 1) as overall_pct,
    enriched_count as food_ready_count
FROM foods_brand_quality_preview_mv
WHERE brand_slug IN ('bozita', 'belcando', 'briantos')
ORDER BY brand_slug;

\echo ''

SELECT 
    'PROD' as view_type,
    brand_slug,
    sku_count,
    ROUND(ingredients_cov, 1) as ingredients_pct,
    ROUND(form_cov, 1) as form_pct,
    ROUND(life_stage_cov, 1) as life_stage_pct,
    ROUND(kcal_cov, 1) as kcal_pct,
    ROUND(completion_pct, 1) as overall_pct,
    enriched_count as food_ready_count
FROM foods_brand_quality_prod_mv
WHERE brand_slug IN ('bozita', 'belcando', 'briantos')
ORDER BY brand_slug;

-- ============================================================================
-- CHECK ACTUAL DATA IN SOURCE TABLES
-- ============================================================================
-- Verify the source data that feeds the MVs

\echo ''
\echo 'Actual coverage in foods_published_preview (source data):'

SELECT 
    brand_slug,
    COUNT(*) as total_skus,
    COUNT(CASE WHEN ingredients_tokens IS NOT NULL 
               AND jsonb_array_length(ingredients_tokens) > 0 THEN 1 END) as with_ingredients,
    COUNT(CASE WHEN form IS NOT NULL THEN 1 END) as with_form,
    COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) as with_life_stage,
    COUNT(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) as with_valid_kcal,
    -- Calculate percentages
    ROUND(100.0 * COUNT(CASE WHEN ingredients_tokens IS NOT NULL 
                             AND jsonb_array_length(ingredients_tokens) > 0 THEN 1 END) / COUNT(*), 1) as ingredients_pct,
    ROUND(100.0 * COUNT(CASE WHEN form IS NOT NULL THEN 1 END) / COUNT(*), 1) as form_pct,
    ROUND(100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*), 1) as life_stage_pct,
    ROUND(100.0 * COUNT(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) / COUNT(*), 1) as kcal_pct
FROM foods_published_preview
WHERE brand_slug IN ('bozita', 'belcando', 'briantos')
GROUP BY brand_slug
ORDER BY brand_slug;

-- ============================================================================
-- SHOW REFRESH TIMESTAMPS
-- ============================================================================
\echo ''
\echo 'Materialized view refresh completed:'

SELECT 
    'AFTER REFRESH' as status,
    schemaname,
    matviewname,
    last_refresh_time
FROM pg_catalog.pg_matviews 
WHERE matviewname IN ('foods_brand_quality_preview_mv', 'foods_brand_quality_prod_mv');

-- Reset timeout
RESET statement_timeout;

-- ============================================================================
-- NOTES
-- ============================================================================
-- If CONCURRENTLY fails with "cannot refresh materialized view concurrently"
-- it means the MV doesn't have a unique index. In that case, remove CONCURRENTLY:
--   REFRESH MATERIALIZED VIEW foods_brand_quality_preview_mv;
--   REFRESH MATERIALIZED VIEW foods_brand_quality_prod_mv;
--
-- To check if concurrent refresh is supported:
-- SELECT indexname FROM pg_indexes 
-- WHERE tablename IN ('foods_brand_quality_preview_mv', 'foods_brand_quality_prod_mv');
-- ============================================================================