-- Refresh materialized views after brand normalization
-- Execute these in order

-- 1. Refresh base materialized view
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_published_materialized;

-- 2. Refresh production view
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_published_prod;

-- 3. Refresh preview view  
REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_published_preview;

-- 4. Verify changes
SELECT brand, COUNT(*) as product_count
FROM foods_published_prod
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;
