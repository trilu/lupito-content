-- Query to generate brand scoreboard manually
SELECT 
    brand_slug,
    brand_name,
    sku_count,
    ROUND(completion_pct, 1) as completion_pct,
    ROUND(form_coverage_pct, 1) as form_pct,
    ROUND(life_stage_coverage_pct, 1) as life_stage_pct,
    ROUND(ingredients_coverage_pct, 1) as ingredients_pct,
    ROUND(kcal_valid_pct, 1) as kcal_pct,
    CASE 
        WHEN form_coverage_pct >= 90 
         AND life_stage_coverage_pct >= 95 
         AND ingredients_coverage_pct >= 85 
         AND kcal_valid_pct >= 90 
        THEN 'PASS'
        WHEN form_coverage_pct >= 81 
         AND life_stage_coverage_pct >= 85.5 
        THEN 'NEAR'
        ELSE 'TODO'
    END as status
FROM 
    foods_brand_quality_preview_mv
ORDER BY 
    completion_pct DESC,
    sku_count DESC;
