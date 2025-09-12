-- Safe version without CONCURRENTLY
-- Use this if the first version gives an error

REFRESH MATERIALIZED VIEW foods_published_prod;
REFRESH MATERIALIZED VIEW foods_published_preview;

-- Verify the refresh worked
SELECT 
    brand,
    COUNT(*) as product_count
FROM foods_canonical
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;