-- Test query that works with the current view structure
-- This query is tolerant of missing nutrition data

SELECT 
  brand, 
  product_name, 
  form,
  life_stage,
  kcal_per_100g,  -- May be NULL
  protein_percent,  -- May be NULL
  fat_percent,  -- May be NULL
  contains_chicken,
  price_eur,
  CASE
    WHEN price_eur IS NULL THEN 'mid'
    WHEN price_eur < 30 THEN 'low'
    WHEN price_eur < 60 THEN 'mid'
    ELSE 'high'
  END AS price_bucket,
  COALESCE(available_countries, ARRAY['EU']::text[]) AS available_countries
FROM foods_published 
LIMIT 5;