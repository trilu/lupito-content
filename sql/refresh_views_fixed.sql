-- Refresh materialized views after brand normalization
-- Execute these in order
-- Note: PostgreSQL doesn't support IF EXISTS with REFRESH MATERIALIZED VIEW

-- 1. Refresh foods_published_prod
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_published_prod;

-- 2. Refresh foods_published_preview
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_published_preview;

-- Verify changes in brand distribution
SELECT 
    brand,
    COUNT(*) as product_count,
    COUNT(DISTINCT brand_slug) as unique_slugs
FROM foods_canonical
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;

-- Check if brand_alias table was created and populated
SELECT 
    COUNT(*) as total_aliases,
    COUNT(DISTINCT canonical_brand) as unique_brands
FROM brand_alias;
