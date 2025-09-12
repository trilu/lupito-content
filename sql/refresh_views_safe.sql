-- Safe refresh of materialized views (without CONCURRENTLY)
-- Use this if the CONCURRENTLY version fails

-- Refresh foods_published_prod
REFRESH MATERIALIZED VIEW foods_published_prod;

-- Refresh foods_published_preview
REFRESH MATERIALIZED VIEW foods_published_preview;

-- Verify the refresh worked
SELECT 
    brand,
    COUNT(*) as product_count
FROM foods_canonical
GROUP BY brand
ORDER BY product_count DESC
LIMIT 10;
