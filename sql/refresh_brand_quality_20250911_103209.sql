-- Refresh the brand quality materialized view for Preview
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;

-- Verify the refresh
SELECT 
    brand_slug,
    brand_name,
    sku_count,
    form_coverage_pct,
    life_stage_coverage_pct,
    ingredients_coverage_pct,
    kcal_valid_pct,
    price_coverage_pct,
    completion_pct,
    last_updated
FROM 
    foods_brand_quality_preview_mv
ORDER BY 
    completion_pct DESC,
    sku_count DESC
LIMIT 5;
