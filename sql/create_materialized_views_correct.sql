-- SQL Script 3: Brand Quality Materialized Views (Corrected for actual columns)
-- Based on actual foods_canonical structure

-- Create foods_brand_quality_prod_mv
CREATE MATERIALIZED VIEW IF NOT EXISTS foods_brand_quality_prod_mv AS
SELECT 
    brand_slug,
    COUNT(*) AS sku_count,
    
    -- Coverage metrics (real data, not empty arrays/nulls)
    COUNT(form) * 100.0 / NULLIF(COUNT(*), 0) AS form_coverage,
    COUNT(life_stage) * 100.0 / NULLIF(COUNT(*), 0) AS life_stage_coverage,
    COUNT(primary_protein) * 100.0 / NULLIF(COUNT(*), 0) AS primary_protein_coverage,
    
    -- Ingredients coverage (non-empty arrays)
    COUNT(CASE 
        WHEN jsonb_typeof(ingredients_tokens) = 'array' 
        AND jsonb_array_length(ingredients_tokens) > 0 
        THEN 1 
    END) * 100.0 / NULLIF(COUNT(*), 0) AS ingredients_coverage,
    
    -- Kcal coverage (valid range 200-600)
    COUNT(CASE 
        WHEN kcal_per_100g BETWEEN 200 AND 600 
        THEN 1 
    END) * 100.0 / NULLIF(COUNT(*), 0) AS kcal_coverage,
    
    -- Price coverage
    COUNT(price_per_kg) * 100.0 / NULLIF(COUNT(*), 0) AS price_coverage,
    COUNT(price_bucket) * 100.0 / NULLIF(COUNT(*), 0) AS price_bucket_coverage,
    
    -- Nutrition coverage
    COUNT(protein_percent) * 100.0 / NULLIF(COUNT(*), 0) AS protein_coverage,
    COUNT(fat_percent) * 100.0 / NULLIF(COUNT(*), 0) AS fat_coverage,
    
    -- Completion percentage (average of key fields)
    (
        COUNT(form) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(life_stage) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(CASE 
            WHEN jsonb_typeof(ingredients_tokens) = 'array' 
            AND jsonb_array_length(ingredients_tokens) > 0 
            THEN 1 
        END) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(CASE 
            WHEN kcal_per_100g BETWEEN 200 AND 600 
            THEN 1 
        END) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(price_per_kg) * 100.0 / NULLIF(COUNT(*), 0)
    ) / 5.0 AS completion_pct,
    
    -- Quality metrics
    AVG(quality_score) AS avg_quality_score,
    
    -- Kcal outliers (outside valid range)
    COUNT(CASE 
        WHEN kcal_per_100g IS NOT NULL 
        AND (kcal_per_100g < 200 OR kcal_per_100g > 600) 
        THEN 1 
    END) AS kcal_outliers,
    
    -- Protein content stats
    COUNT(has_chicken) FILTER (WHERE has_chicken = true) AS has_chicken_count,
    COUNT(has_poultry) FILTER (WHERE has_poultry = true) AS has_poultry_count,
    
    NOW() AS last_refreshed_at,
    allowlist_status
FROM foods_published_prod
GROUP BY brand_slug, allowlist_status;

-- Create foods_brand_quality_preview_mv
CREATE MATERIALIZED VIEW IF NOT EXISTS foods_brand_quality_preview_mv AS
SELECT 
    brand_slug,
    COUNT(*) AS sku_count,
    
    -- Coverage metrics (real data, not empty arrays/nulls)
    COUNT(form) * 100.0 / NULLIF(COUNT(*), 0) AS form_coverage,
    COUNT(life_stage) * 100.0 / NULLIF(COUNT(*), 0) AS life_stage_coverage,
    COUNT(primary_protein) * 100.0 / NULLIF(COUNT(*), 0) AS primary_protein_coverage,
    
    -- Ingredients coverage (non-empty arrays)
    COUNT(CASE 
        WHEN jsonb_typeof(ingredients_tokens) = 'array' 
        AND jsonb_array_length(ingredients_tokens) > 0 
        THEN 1 
    END) * 100.0 / NULLIF(COUNT(*), 0) AS ingredients_coverage,
    
    -- Kcal coverage (valid range 200-600)
    COUNT(CASE 
        WHEN kcal_per_100g BETWEEN 200 AND 600 
        THEN 1 
    END) * 100.0 / NULLIF(COUNT(*), 0) AS kcal_coverage,
    
    -- Price coverage
    COUNT(price_per_kg) * 100.0 / NULLIF(COUNT(*), 0) AS price_coverage,
    COUNT(price_bucket) * 100.0 / NULLIF(COUNT(*), 0) AS price_bucket_coverage,
    
    -- Nutrition coverage
    COUNT(protein_percent) * 100.0 / NULLIF(COUNT(*), 0) AS protein_coverage,
    COUNT(fat_percent) * 100.0 / NULLIF(COUNT(*), 0) AS fat_coverage,
    
    -- Completion percentage (average of key fields)
    (
        COUNT(form) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(life_stage) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(CASE 
            WHEN jsonb_typeof(ingredients_tokens) = 'array' 
            AND jsonb_array_length(ingredients_tokens) > 0 
            THEN 1 
        END) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(CASE 
            WHEN kcal_per_100g BETWEEN 200 AND 600 
            THEN 1 
        END) * 100.0 / NULLIF(COUNT(*), 0) +
        COUNT(price_per_kg) * 100.0 / NULLIF(COUNT(*), 0)
    ) / 5.0 AS completion_pct,
    
    -- Quality metrics
    AVG(quality_score) AS avg_quality_score,
    
    -- Kcal outliers (outside valid range)
    COUNT(CASE 
        WHEN kcal_per_100g IS NOT NULL 
        AND (kcal_per_100g < 200 OR kcal_per_100g > 600) 
        THEN 1 
    END) AS kcal_outliers,
    
    -- Protein content stats
    COUNT(has_chicken) FILTER (WHERE has_chicken = true) AS has_chicken_count,
    COUNT(has_poultry) FILTER (WHERE has_poultry = true) AS has_poultry_count,
    
    NOW() AS last_refreshed_at,
    allowlist_status
FROM foods_published_preview
GROUP BY brand_slug, allowlist_status;

-- Refresh materialized views
REFRESH MATERIALIZED VIEW foods_brand_quality_prod_mv;
REFRESH MATERIALIZED VIEW foods_brand_quality_preview_mv;

-- Create indexes on MVs for performance
CREATE INDEX IF NOT EXISTS idx_brand_quality_prod_brand_slug 
    ON foods_brand_quality_prod_mv (brand_slug);
CREATE INDEX IF NOT EXISTS idx_brand_quality_prod_completion 
    ON foods_brand_quality_prod_mv (completion_pct DESC);
CREATE INDEX IF NOT EXISTS idx_brand_quality_prod_quality 
    ON foods_brand_quality_prod_mv (avg_quality_score DESC);

CREATE INDEX IF NOT EXISTS idx_brand_quality_preview_brand_slug 
    ON foods_brand_quality_preview_mv (brand_slug);
CREATE INDEX IF NOT EXISTS idx_brand_quality_preview_completion 
    ON foods_brand_quality_preview_mv (completion_pct DESC);
CREATE INDEX IF NOT EXISTS idx_brand_quality_preview_quality 
    ON foods_brand_quality_preview_mv (avg_quality_score DESC);

-- Grant permissions (uncomment and adjust roles as needed)
-- GRANT SELECT ON foods_brand_quality_prod_mv TO anon;
-- GRANT SELECT ON foods_brand_quality_prod_mv TO authenticated;
-- GRANT SELECT ON foods_brand_quality_prod_mv TO service_role;
-- GRANT SELECT ON foods_brand_quality_preview_mv TO anon;
-- GRANT SELECT ON foods_brand_quality_preview_mv TO authenticated;
-- GRANT SELECT ON foods_brand_quality_preview_mv TO service_role;