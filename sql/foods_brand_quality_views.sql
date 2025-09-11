-- ============================================================================
-- BRAND QUALITY METRICS VIEWS
-- Purpose: Enable fast querying of brand-level quality metrics for Admin
-- Generated: 2025-09-10
-- ============================================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS foods_brand_quality_preview CASCADE;
DROP VIEW IF EXISTS foods_brand_quality_prod CASCADE;
DROP MATERIALIZED VIEW IF EXISTS foods_brand_quality_preview_mv CASCADE;
DROP MATERIALIZED VIEW IF EXISTS foods_brand_quality_prod_mv CASCADE;

-- ============================================================================
-- PREVIEW VIEW (All brands with full enrichment testing)
-- ============================================================================

CREATE MATERIALIZED VIEW foods_brand_quality_preview_mv AS
WITH brand_metrics AS (
    SELECT 
        brand_slug,
        COUNT(*) AS sku_count,
        
        -- Coverage calculations (percentage with non-null values)
        ROUND(COUNT(form) * 100.0 / NULLIF(COUNT(*), 0), 2) AS form_cov,
        ROUND(COUNT(life_stage) * 100.0 / NULLIF(COUNT(*), 0), 2) AS life_stage_cov,
        ROUND(COUNT(ingredients) * 100.0 / NULLIF(COUNT(*), 0), 2) AS ingredients_cov,
        ROUND(COUNT(kcal_per_100g) * 100.0 / NULLIF(COUNT(*), 0), 2) AS kcal_cov,
        ROUND(COUNT(price) * 100.0 / NULLIF(COUNT(*), 0), 2) AS price_cov,
        ROUND(COUNT(price_bucket) * 100.0 / NULLIF(COUNT(*), 0), 2) AS price_bucket_cov,
        
        -- Count outliers (kcal outside 200-600 range)
        COUNT(CASE 
            WHEN kcal_per_100g IS NOT NULL 
                AND (kcal_per_100g < 200 OR kcal_per_100g > 600) 
            THEN 1 
        END) AS kcal_outliers,
        
        -- Count price outliers for additional monitoring
        COUNT(CASE 
            WHEN price IS NOT NULL 
                AND (price < 1 OR price > 200) 
            THEN 1 
        END) AS price_outliers
        
    FROM foods_published_preview
    GROUP BY brand_slug
),
brand_status AS (
    SELECT 
        *,
        -- Calculate completion percentage (average of 5 key coverages)
        ROUND((
            COALESCE(form_cov, 0) + 
            COALESCE(life_stage_cov, 0) + 
            COALESCE(ingredients_cov, 0) + 
            COALESCE(kcal_cov, 0) + 
            COALESCE(price_cov, 0)
        ) / 5.0, 2) AS completion_pct,
        
        -- Determine status based on thresholds
        CASE
            -- PASS: All quality gates met
            WHEN form_cov >= 95 
                AND life_stage_cov >= 95 
                AND ingredients_cov >= 85 
                AND price_bucket_cov >= 70 
                AND kcal_outliers = 0
            THEN 'PASS'
            
            -- NEAR: Within 5 percentage points of passing
            WHEN form_cov >= 90 
                AND life_stage_cov >= 90 
                AND ingredients_cov >= 80 
                AND price_bucket_cov >= 65 
                AND kcal_outliers <= 2
            THEN 'NEAR'
            
            -- TODO: Needs significant work
            ELSE 'TODO'
        END AS status,
        
        -- Additional helpful flags
        CASE WHEN form_cov >= 95 THEN true ELSE false END AS form_pass,
        CASE WHEN life_stage_cov >= 95 THEN true ELSE false END AS life_stage_pass,
        CASE WHEN ingredients_cov >= 85 THEN true ELSE false END AS ingredients_pass,
        CASE WHEN price_bucket_cov >= 70 THEN true ELSE false END AS price_bucket_pass,
        CASE WHEN kcal_outliers = 0 THEN true ELSE false END AS kcal_pass
        
    FROM brand_metrics
)
SELECT 
    brand_slug,
    sku_count,
    form_cov,
    life_stage_cov,
    ingredients_cov,
    kcal_cov,
    price_cov,
    price_bucket_cov,
    completion_pct,
    kcal_outliers,
    status,
    form_pass,
    life_stage_pass,
    ingredients_pass,
    price_bucket_pass,
    kcal_pass,
    CURRENT_TIMESTAMP AS last_refreshed_at
FROM brand_status
ORDER BY sku_count DESC;

-- Create indexes for fast querying
CREATE INDEX idx_brand_quality_preview_brand ON foods_brand_quality_preview_mv(brand_slug);
CREATE INDEX idx_brand_quality_preview_sku_count ON foods_brand_quality_preview_mv(sku_count DESC);
CREATE INDEX idx_brand_quality_preview_status ON foods_brand_quality_preview_mv(status);
CREATE INDEX idx_brand_quality_preview_completion ON foods_brand_quality_preview_mv(completion_pct DESC);

-- ============================================================================
-- PRODUCTION VIEW (Only allowlisted brands in production)
-- Uses brand_allowlist table for transparent control
-- ============================================================================

CREATE MATERIALIZED VIEW foods_brand_quality_prod_mv AS
WITH brand_metrics AS (
    SELECT 
        f.brand_slug,
        COUNT(*) AS sku_count,
        
        -- Coverage calculations
        ROUND(COUNT(f.form) * 100.0 / NULLIF(COUNT(*), 0), 2) AS form_cov,
        ROUND(COUNT(f.life_stage) * 100.0 / NULLIF(COUNT(*), 0), 2) AS life_stage_cov,
        ROUND(COUNT(f.ingredients) * 100.0 / NULLIF(COUNT(*), 0), 2) AS ingredients_cov,
        ROUND(COUNT(f.kcal_per_100g) * 100.0 / NULLIF(COUNT(*), 0), 2) AS kcal_cov,
        ROUND(COUNT(f.price) * 100.0 / NULLIF(COUNT(*), 0), 2) AS price_cov,
        ROUND(COUNT(f.price_bucket) * 100.0 / NULLIF(COUNT(*), 0), 2) AS price_bucket_cov,
        
        -- Count outliers
        COUNT(CASE 
            WHEN f.kcal_per_100g IS NOT NULL 
                AND (f.kcal_per_100g < 200 OR f.kcal_per_100g > 600) 
            THEN 1 
        END) AS kcal_outliers,
        
        -- Production-specific metrics from allowlist
        MAX(CASE WHEN a.status = 'ACTIVE' THEN 1 ELSE 0 END) AS is_active,
        MAX(a.status) AS allowlist_status,
        MAX(a.last_validated) AS allowlist_validated_at,
        COUNT(CASE WHEN a.status = 'ACTIVE' THEN 1 END) AS enriched_count
        
    FROM foods_published_prod f
    LEFT JOIN brand_allowlist a ON f.brand_slug = a.brand_slug
    GROUP BY f.brand_slug
),
brand_status AS (
    SELECT 
        *,
        -- Calculate completion percentage
        ROUND((
            COALESCE(form_cov, 0) + 
            COALESCE(life_stage_cov, 0) + 
            COALESCE(ingredients_cov, 0) + 
            COALESCE(kcal_cov, 0) + 
            COALESCE(price_cov, 0)
        ) / 5.0, 2) AS completion_pct,
        
        -- Calculate enrichment rate
        ROUND(enriched_count * 100.0 / NULLIF(sku_count, 0), 2) AS enrichment_rate,
        
        -- Include allowlist status
        allowlist_status,
        allowlist_validated_at,
        is_active,
        
        -- Determine status
        CASE
            WHEN form_cov >= 95 
                AND life_stage_cov >= 95 
                AND ingredients_cov >= 85 
                AND price_bucket_cov >= 70 
                AND kcal_outliers = 0
            THEN 'PASS'
            WHEN form_cov >= 90 
                AND life_stage_cov >= 90 
                AND ingredients_cov >= 80 
                AND price_bucket_cov >= 65 
                AND kcal_outliers <= 2
            THEN 'NEAR'
            ELSE 'TODO'
        END AS status
        
    FROM brand_metrics
)
SELECT 
    brand_slug,
    sku_count,
    form_cov,
    life_stage_cov,
    ingredients_cov,
    kcal_cov,
    price_cov,
    price_bucket_cov,
    completion_pct,
    kcal_outliers,
    status,
    allowlist_status,
    is_active,
    enriched_count,
    enrichment_rate,
    allowlist_validated_at,
    CURRENT_TIMESTAMP AS last_refreshed_at
FROM brand_status
ORDER BY sku_count DESC;

-- Create indexes
CREATE INDEX idx_brand_quality_prod_brand ON foods_brand_quality_prod_mv(brand_slug);
CREATE INDEX idx_brand_quality_prod_sku_count ON foods_brand_quality_prod_mv(sku_count DESC);
CREATE INDEX idx_brand_quality_prod_status ON foods_brand_quality_prod_mv(status);
CREATE INDEX idx_brand_quality_prod_completion ON foods_brand_quality_prod_mv(completion_pct DESC);

-- ============================================================================
-- CONVENIENCE VIEWS (Non-materialized for real-time queries)
-- ============================================================================

-- Simple view for preview environment
CREATE OR REPLACE VIEW foods_brand_quality_preview AS
SELECT * FROM foods_brand_quality_preview_mv;

-- Simple view for production environment
CREATE OR REPLACE VIEW foods_brand_quality_prod AS
SELECT * FROM foods_brand_quality_prod_mv;

-- ============================================================================
-- REFRESH FUNCTIONS
-- ============================================================================

-- Function to refresh preview metrics
CREATE OR REPLACE FUNCTION refresh_brand_quality_preview()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh production metrics
CREATE OR REPLACE FUNCTION refresh_brand_quality_prod()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_prod_mv;
END;
$$ LANGUAGE plpgsql;

-- Function to refresh both views
CREATE OR REPLACE FUNCTION refresh_all_brand_quality()
RETURNS void AS $$
BEGIN
    PERFORM refresh_brand_quality_preview();
    PERFORM refresh_brand_quality_prod();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SCHEDULED REFRESH (Requires pg_cron extension)
-- ============================================================================

-- Uncomment if pg_cron is available
-- SELECT cron.schedule('refresh-brand-quality', '0 2 * * *', 'SELECT refresh_all_brand_quality();');

-- ============================================================================
-- USEFUL QUERIES
-- ============================================================================

-- Get top 20 brands by SKU count with status
/*
SELECT 
    brand_slug,
    sku_count,
    completion_pct,
    status,
    CASE 
        WHEN status = 'PASS' THEN '✅'
        WHEN status = 'NEAR' THEN '🔶'
        ELSE '❌'
    END AS status_icon
FROM foods_brand_quality_preview
ORDER BY sku_count DESC
LIMIT 20;
*/

-- Get brands close to passing (NEAR status)
/*
SELECT 
    brand_slug,
    sku_count,
    form_cov,
    life_stage_cov,
    ingredients_cov,
    price_bucket_cov,
    kcal_outliers,
    95 - form_cov AS form_gap,
    95 - life_stage_cov AS life_stage_gap,
    85 - ingredients_cov AS ingredients_gap,
    70 - price_bucket_cov AS price_bucket_gap
FROM foods_brand_quality_preview
WHERE status = 'NEAR'
ORDER BY completion_pct DESC;
*/

-- Get production deployment candidates
/*
SELECT 
    brand_slug,
    sku_count,
    completion_pct,
    status
FROM foods_brand_quality_preview
WHERE status = 'PASS'
    AND brand_slug NOT IN (
        SELECT DISTINCT brand_slug 
        FROM foods_published_prod 
        WHERE production_allowlist = true
    )
ORDER BY sku_count DESC;
*/

-- ============================================================================
-- GRANTS (Adjust as needed)
-- ============================================================================

-- GRANT SELECT ON foods_brand_quality_preview TO admin_role;
-- GRANT SELECT ON foods_brand_quality_prod TO admin_role;
-- GRANT EXECUTE ON FUNCTION refresh_all_brand_quality() TO admin_role;