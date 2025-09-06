-- Verification queries for foods_published deduplication logic

-- 1. Count total products vs deduplicated products
SELECT 
  (SELECT COUNT(*) FROM food_candidates WHERE brand IS NOT NULL AND product_name IS NOT NULL) as total_candidates,
  (SELECT COUNT(*) FROM foods_published) as published_products,
  (SELECT COUNT(*) FROM food_candidates WHERE brand IS NOT NULL AND product_name IS NOT NULL) - 
  (SELECT COUNT(*) FROM foods_published) as duplicates_removed;

-- 2. Check nutrition data availability before/after dedup
SELECT 
  'Before Dedup (food_candidates)' as source,
  COUNT(*) as total_rows,
  SUM((kcal_per_100g IS NOT NULL)::int) as with_kcal,
  SUM((kcal_per_100g IS NULL)::int) as without_kcal,
  ROUND(100.0 * SUM((kcal_per_100g IS NOT NULL)::int) / COUNT(*), 1) as kcal_coverage_pct
FROM food_candidates
WHERE brand IS NOT NULL AND product_name IS NOT NULL

UNION ALL

SELECT 
  'After Dedup (foods_published)' as source,
  COUNT(*) as total_rows,
  SUM((kcal_per_100g IS NOT NULL)::int) as with_kcal,
  SUM((kcal_per_100g IS NULL)::int) as without_kcal,
  ROUND(100.0 * SUM((kcal_per_100g IS NOT NULL)::int) / COUNT(*), 1) as kcal_coverage_pct
FROM foods_published;

-- 3. Show source domain distribution in published view
SELECT 
  source_domain,
  COUNT(*) as product_count,
  SUM((kcal_per_100g IS NOT NULL)::int) as with_kcal,
  SUM((protein_percent IS NOT NULL)::int) as with_protein,
  SUM((fat_percent IS NOT NULL)::int) as with_fat,
  ROUND(100.0 * SUM((kcal_per_100g IS NOT NULL)::int) / COUNT(*), 1) as kcal_coverage_pct
FROM foods_published
GROUP BY source_domain
ORDER BY product_count DESC;

-- 4. Examples of deduplicated products (showing which source won)
SELECT 
  brand,
  product_name,
  source_domain as winning_source,
  kcal_per_100g,
  protein_percent,
  fat_percent,
  has_complete_nutrition
FROM foods_published
WHERE brand_slug IN (
  -- Find products that exist in multiple candidates (duplicates)
  SELECT brand_slug
  FROM (
    SELECT 
      LOWER(TRIM(REGEXP_REPLACE(brand, '[^a-zA-Z0-9]+', '-', 'g'))) AS brand_slug,
      LOWER(TRIM(REGEXP_REPLACE(product_name, '[^a-zA-Z0-9]+', '-', 'g'))) AS name_slug,
      COUNT(DISTINCT source_domain) as source_count
    FROM food_candidates
    WHERE brand IS NOT NULL AND product_name IS NOT NULL
    GROUP BY 1, 2
    HAVING COUNT(DISTINCT source_domain) > 1
  ) dupe_check
  GROUP BY brand_slug
  LIMIT 5
)
ORDER BY brand, product_name;

-- 5. Check for potential dedup issues (same brand+name but different winning sources)
WITH potential_issues AS (
  SELECT 
    brand_slug,
    name_slug,
    COUNT(*) as published_count
  FROM foods_published
  GROUP BY brand_slug, name_slug
  HAVING COUNT(*) > 1
)
SELECT 
  pi.brand_slug,
  pi.name_slug,
  pi.published_count,
  fp.brand,
  fp.product_name,
  fp.source_domain
FROM potential_issues pi
JOIN foods_published fp ON fp.brand_slug = pi.brand_slug AND fp.name_slug = pi.name_slug
ORDER BY pi.published_count DESC, pi.brand_slug, pi.name_slug;