-- ============================================================================
-- CHECK VIEW EXISTENCE AND REFRESH STATUS
-- Purpose: Verify materialized views exist and show refresh status
-- ============================================================================

-- Check if views exist in public schema
SELECT 
    schemaname,
    matviewname as view_name,
    matviewowner as owner,
    hasindexes,
    ispopulated,
    definition IS NOT NULL as has_definition
FROM pg_matviews
WHERE schemaname = 'public'
    AND matviewname IN (
        'foods_brand_quality_preview_mv',
        'foods_brand_quality_prod_mv'
    )
ORDER BY matviewname;

-- Check regular views
SELECT 
    schemaname,
    viewname as view_name,
    viewowner as owner,
    definition IS NOT NULL as has_definition
FROM pg_views
WHERE schemaname = 'public'
    AND viewname IN (
        'foods_brand_quality_preview',
        'foods_brand_quality_prod'
    )
ORDER BY viewname;

-- Get last refresh time (if pg_stat_user_tables available)
SELECT 
    schemaname,
    tablename,
    n_tup_ins as rows_inserted,
    n_tup_upd as rows_updated,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND tablename IN (
        'foods_brand_quality_preview_mv',
        'foods_brand_quality_prod_mv'
    );

-- Simple existence check for Admin
SELECT 
    'foods_brand_quality_preview_mv' as view_name,
    EXISTS(
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname = 'foods_brand_quality_preview_mv'
    ) as exists_in_public
UNION ALL
SELECT 
    'foods_brand_quality_prod_mv' as view_name,
    EXISTS(
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname = 'foods_brand_quality_prod_mv'
    ) as exists_in_public
UNION ALL
SELECT 
    'foods_brand_quality_preview' as view_name,
    EXISTS(
        SELECT 1 FROM pg_views 
        WHERE schemaname = 'public' 
        AND viewname = 'foods_brand_quality_preview'
    ) as exists_in_public
UNION ALL
SELECT 
    'foods_brand_quality_prod' as view_name,
    EXISTS(
        SELECT 1 FROM pg_views 
        WHERE schemaname = 'public' 
        AND viewname = 'foods_brand_quality_prod'
    ) as exists_in_public;

-- If views need to be created/refreshed:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_prod_mv;