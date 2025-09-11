-- Refresh the brand quality materialized view for Preview
-- Note: This assumes the materialized view exists. If not, it needs to be created first.

-- Check if the materialized view exists
SELECT EXISTS (
    SELECT 1 
    FROM pg_matviews 
    WHERE matviewname = 'foods_brand_quality_preview_mv'
) AS view_exists;

-- If it exists, refresh it
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;

-- Verify the refresh by checking brand metrics
SELECT 
    brand_slug,
    COUNT(*) as product_count,
    COUNT(CASE WHEN form IS NOT NULL THEN 1 END) as form_filled,
    COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) as life_stage_filled,
    ROUND(100.0 * COUNT(CASE WHEN form IS NOT NULL THEN 1 END) / COUNT(*), 1) as form_pct,
    ROUND(100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*), 1) as life_stage_pct
FROM 
    foods_published_preview
GROUP BY 
    brand_slug
ORDER BY 
    product_count DESC
LIMIT 10;