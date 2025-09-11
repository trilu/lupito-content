-- Create the brand quality materialized view for Preview
DROP MATERIALIZED VIEW IF EXISTS foods_brand_quality_preview_mv;

CREATE MATERIALIZED VIEW foods_brand_quality_preview_mv AS
SELECT 
    brand_slug,
    MAX(brand) as brand_name,
    COUNT(*) as sku_count,
    
    -- Coverage percentages
    ROUND(100.0 * COUNT(CASE WHEN form IS NOT NULL THEN 1 END) / COUNT(*), 2) as form_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*), 2) as life_stage_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN json_array_length(ingredients_tokens::json) > 0 THEN 1 END) / COUNT(*), 2) as ingredients_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) / COUNT(*), 2) as kcal_valid_pct,
    ROUND(100.0 * COUNT(CASE WHEN price_per_kg IS NOT NULL THEN 1 END) / COUNT(*), 2) as price_coverage_pct,
    
    -- Overall completion percentage (average of all metrics)
    ROUND((
        100.0 * COUNT(CASE WHEN form IS NOT NULL THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN json_array_length(ingredients_tokens::json) > 0 THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN price_per_kg IS NOT NULL THEN 1 END) / COUNT(*)
    ) / 5, 2) as completion_pct,
    
    -- Counts by life stage
    COUNT(CASE WHEN life_stage = 'puppy' THEN 1 END) as puppy_count,
    COUNT(CASE WHEN life_stage = 'adult' THEN 1 END) as adult_count,
    COUNT(CASE WHEN life_stage = 'senior' THEN 1 END) as senior_count,
    
    -- Counts by form
    COUNT(CASE WHEN form = 'dry' THEN 1 END) as dry_count,
    COUNT(CASE WHEN form = 'wet' THEN 1 END) as wet_count,
    COUNT(CASE WHEN form = 'treats' THEN 1 END) as treats_count,
    
    NOW() as last_updated
FROM 
    foods_published_preview
GROUP BY 
    brand_slug;

-- Create index for faster access
CREATE INDEX idx_brand_quality_preview_brand_slug ON foods_brand_quality_preview_mv(brand_slug);
CREATE INDEX idx_brand_quality_preview_completion ON foods_brand_quality_preview_mv(completion_pct DESC);

-- Grant permissions
GRANT SELECT ON foods_brand_quality_preview_mv TO authenticated;
GRANT SELECT ON foods_brand_quality_preview_mv TO anon;

-- Also create the Production version
DROP MATERIALIZED VIEW IF EXISTS foods_brand_quality_prod_mv;

CREATE MATERIALIZED VIEW foods_brand_quality_prod_mv AS
SELECT 
    brand_slug,
    MAX(brand) as brand_name,
    COUNT(*) as sku_count,
    
    -- Coverage percentages
    ROUND(100.0 * COUNT(CASE WHEN form IS NOT NULL THEN 1 END) / COUNT(*), 2) as form_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*), 2) as life_stage_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN json_array_length(ingredients_tokens::json) > 0 THEN 1 END) / COUNT(*), 2) as ingredients_coverage_pct,
    ROUND(100.0 * COUNT(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) / COUNT(*), 2) as kcal_valid_pct,
    ROUND(100.0 * COUNT(CASE WHEN price_per_kg IS NOT NULL THEN 1 END) / COUNT(*), 2) as price_coverage_pct,
    
    -- Overall completion percentage
    ROUND((
        100.0 * COUNT(CASE WHEN form IS NOT NULL THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN json_array_length(ingredients_tokens::json) > 0 THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 END) / COUNT(*) +
        100.0 * COUNT(CASE WHEN price_per_kg IS NOT NULL THEN 1 END) / COUNT(*)
    ) / 5, 2) as completion_pct,
    
    -- Counts by life stage
    COUNT(CASE WHEN life_stage = 'puppy' THEN 1 END) as puppy_count,
    COUNT(CASE WHEN life_stage = 'adult' THEN 1 END) as adult_count,
    COUNT(CASE WHEN life_stage = 'senior' THEN 1 END) as senior_count,
    
    -- Counts by form
    COUNT(CASE WHEN form = 'dry' THEN 1 END) as dry_count,
    COUNT(CASE WHEN form = 'wet' THEN 1 END) as wet_count,
    COUNT(CASE WHEN form = 'treats' THEN 1 END) as treats_count,
    
    NOW() as last_updated
FROM 
    foods_published_prod
GROUP BY 
    brand_slug;

-- Create index for Production version
CREATE INDEX idx_brand_quality_prod_brand_slug ON foods_brand_quality_prod_mv(brand_slug);
CREATE INDEX idx_brand_quality_prod_completion ON foods_brand_quality_prod_mv(completion_pct DESC);

-- Grant permissions
GRANT SELECT ON foods_brand_quality_prod_mv TO authenticated;
GRANT SELECT ON foods_brand_quality_prod_mv TO anon;

-- Verify creation
SELECT 
    'Preview' as environment,
    COUNT(*) as brand_count,
    ROUND(AVG(completion_pct), 2) as avg_completion,
    SUM(sku_count) as total_skus
FROM foods_brand_quality_preview_mv
UNION ALL
SELECT 
    'Production' as environment,
    COUNT(*) as brand_count,
    ROUND(AVG(completion_pct), 2) as avg_completion,
    SUM(sku_count) as total_skus
FROM foods_brand_quality_prod_mv;