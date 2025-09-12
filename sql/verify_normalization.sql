-- Verify brand normalization is working
-- This shows the current brand distribution

SELECT 
    brand,
    COUNT(*) as product_count
FROM foods_published_prod
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY product_count DESC
LIMIT 20;

-- Check specific normalized brands
SELECT brand, COUNT(*) as count
FROM foods_published_prod
WHERE brand IN ('Arden Grange', 'Barking Heads', 'Bosch')
GROUP BY brand;

-- Check foods_canonical directly
SELECT brand, COUNT(*) as count
FROM foods_canonical
WHERE brand IN ('Arden Grange', 'Barking Heads', 'Bosch')
GROUP BY brand;
