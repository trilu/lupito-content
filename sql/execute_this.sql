-- Execute this SQL in Supabase SQL Editor
-- Copy and paste ONLY this content

-- Refresh the materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_published_prod;
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_published_preview;

-- Verify the refresh worked
SELECT 
    brand,
    COUNT(*) as product_count
FROM foods_canonical
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;