-- Fix Missing Brand Slugs - Massive Auto-Approval Opportunity
-- This will generate brand_slugs for 4,254 products with NULL brand_slugs
-- Then add the new brands to allowlist for instant approval

-- STEP 1: Check current state
SELECT
  'NULL brand_slugs in canonical' as status,
  COUNT(*) as count
FROM foods_canonical
WHERE brand_slug IS NULL AND brand IS NOT NULL;

SELECT
  'NULL brand_slugs in preview (PENDING)' as status,
  COUNT(*) as count
FROM foods_published_preview
WHERE brand_slug IS NULL AND allowlist_status = 'PENDING';

-- STEP 2: Preview the brand slug generation
-- This shows what brand_slugs would be generated
WITH slug_generation AS (
  SELECT
    brand,
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(brand), '[^a-zA-Z0-9\s]+', '', 'g'), '\s+', '-', 'g')) as generated_slug,
    COUNT(*) as product_count
  FROM foods_canonical
  WHERE brand_slug IS NULL AND brand IS NOT NULL
  GROUP BY brand
)
SELECT
  COUNT(*) as unique_brands_to_slug,
  SUM(product_count) as total_products_affected
FROM slug_generation;

-- Show sample conversions
WITH slug_generation AS (
  SELECT
    brand,
    LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(brand), '[^a-zA-Z0-9\s]+', '', 'g'), '\s+', '-', 'g')) as generated_slug,
    COUNT(*) as product_count
  FROM foods_canonical
  WHERE brand_slug IS NULL AND brand IS NOT NULL
  GROUP BY brand
)
SELECT brand, generated_slug, product_count
FROM slug_generation
ORDER BY product_count DESC
LIMIT 10;

-- STEP 3: Execute brand_slug generation (UNCOMMENT TO RUN):
/*
UPDATE foods_canonical
SET brand_slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(brand), '[^a-zA-Z0-9\s]+', '', 'g'), '\s+', '-', 'g'))
WHERE brand_slug IS NULL
  AND brand IS NOT NULL
  AND brand != '';
*/

-- STEP 4: After brand_slug generation, add new brands to allowlist (UNCOMMENT TO RUN):
/*
WITH new_brands AS (
  SELECT DISTINCT brand_slug
  FROM foods_canonical fc
  WHERE brand_slug IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM brand_allowlist ba
      WHERE ba.brand_slug = fc.brand_slug
    )
    -- Only add brands with quality products
    AND EXISTS (
      SELECT 1 FROM foods_published_preview fpp
      WHERE fpp.brand_slug = fc.brand_slug
        AND fpp.image_url IS NOT NULL
        AND fpp.ingredients_tokens IS NOT NULL
        AND (fpp.protein_percent IS NOT NULL OR fpp.fat_percent IS NOT NULL OR fpp.kcal_per_100g IS NOT NULL)
    )
)
INSERT INTO brand_allowlist (brand_slug, status, created_at, updated_at, notes)
SELECT
  brand_slug,
  'ACTIVE',
  NOW(),
  NOW(),
  'Auto-approved: Generated brand_slug + quality products'
FROM new_brands;
*/

-- STEP 5: Verify the massive impact (UNCOMMENT TO RUN AFTER EXECUTION):
/*
-- Check brand_slug generation success
SELECT
  'Products with brand_slugs after fix' as status,
  COUNT(*) as count
FROM foods_canonical
WHERE brand_slug IS NOT NULL;

-- Check new allowlist size
SELECT COUNT(*) as total_allowlist_brands FROM brand_allowlist;

-- Check final product distribution - should show MASSIVE increase in ACTIVE
SELECT
  allowlist_status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM foods_published_preview
GROUP BY allowlist_status
ORDER BY allowlist_status;

-- Expected results:
-- Before: ~5,051 ACTIVE + ~4,288 PENDING = 9,339 total
-- After: Could be ~8,000+ ACTIVE + ~1,000+ PENDING = 9,339 total
-- Impact: +60% additional production increase!
*/