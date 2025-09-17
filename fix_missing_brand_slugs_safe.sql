-- Fix Missing Brand Slugs - SAFE Approach
-- This handles both conflicts (same brands) and new brands safely

-- STEP 1: Check current state
SELECT 'NULL brand_slugs total' as status, COUNT(*) as count
FROM foods_canonical
WHERE brand_slug IS NULL AND brand IS NOT NULL;

-- STEP 2: Preview the two-part fix

-- Part A: Copy existing slugs for same brands (conflicts)
WITH existing_brand_slugs AS (
  SELECT DISTINCT brand, brand_slug
  FROM foods_canonical
  WHERE brand_slug IS NOT NULL
),
conflicting_brands AS (
  SELECT
    fc.product_key,
    fc.brand,
    ebs.brand_slug as existing_slug
  FROM foods_canonical fc
  JOIN existing_brand_slugs ebs ON fc.brand = ebs.brand
  WHERE fc.brand_slug IS NULL
    AND fc.brand IS NOT NULL
)
SELECT 'Products to copy existing slugs' as action, COUNT(*) as count
FROM conflicting_brands;

-- Part B: Generate new slugs for truly new brands
WITH existing_brand_names AS (
  SELECT DISTINCT brand
  FROM foods_canonical
  WHERE brand_slug IS NOT NULL
),
new_brands AS (
  SELECT DISTINCT brand
  FROM foods_canonical fc
  WHERE fc.brand_slug IS NULL
    AND fc.brand IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM existing_brand_names ebn
      WHERE ebn.brand = fc.brand
    )
)
SELECT 'New brands needing fresh slugs' as action, COUNT(*) as count
FROM new_brands;

-- STEP 3: Execute Part A - Copy existing slugs for same brands (UNCOMMENT TO RUN):
/*
WITH existing_brand_slugs AS (
  SELECT
    brand,
    brand_slug,
    ROW_NUMBER() OVER (PARTITION BY brand ORDER BY brand_slug) as rn
  FROM foods_canonical
  WHERE brand_slug IS NOT NULL
),
unique_brand_slugs AS (
  SELECT brand, brand_slug
  FROM existing_brand_slugs
  WHERE rn = 1  -- Take first slug if multiple exist for same brand
)
UPDATE foods_canonical
SET brand_slug = (
  SELECT ubs.brand_slug
  FROM unique_brand_slugs ubs
  WHERE ubs.brand = foods_canonical.brand
)
WHERE brand_slug IS NULL
  AND brand IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM unique_brand_slugs ubs
    WHERE ubs.brand = foods_canonical.brand
  );
*/

-- STEP 4: Execute Part B - Generate slugs for truly new brands (UNCOMMENT TO RUN):
/*
WITH existing_brand_names AS (
  SELECT DISTINCT brand
  FROM foods_canonical
  WHERE brand_slug IS NOT NULL
)
UPDATE foods_canonical
SET brand_slug = LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(brand), '[^a-zA-Z0-9\s]+', '', 'g'), '\s+', '-', 'g'))
WHERE brand_slug IS NULL
  AND brand IS NOT NULL
  AND brand != ''
  AND NOT EXISTS (
    SELECT 1 FROM existing_brand_names ebn
    WHERE ebn.brand = foods_canonical.brand
  );
*/

-- STEP 5: Add newly-slugged quality brands to allowlist (UNCOMMENT TO RUN):
/*
WITH new_quality_brands AS (
  SELECT DISTINCT fc.brand_slug
  FROM foods_canonical fc
  WHERE fc.brand_slug IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM brand_allowlist ba
      WHERE ba.brand_slug = fc.brand_slug
    )
    -- Only quality brands
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
  'Auto-approved: Brand slug fix + quality products'
FROM new_quality_brands;
*/

-- STEP 6: Verify the results (UNCOMMENT TO RUN AFTER EXECUTION):
/*
-- Check slug fix success
SELECT 'Products with brand_slugs after fix' as status, COUNT(*) as count
FROM foods_canonical
WHERE brand_slug IS NOT NULL;

SELECT 'Products still missing brand_slugs' as status, COUNT(*) as count
FROM foods_canonical
WHERE brand_slug IS NULL AND brand IS NOT NULL;

-- Check allowlist growth
SELECT COUNT(*) as total_allowlist_brands FROM brand_allowlist;

-- Check massive product approval
SELECT
  allowlist_status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM foods_published_preview
GROUP BY allowlist_status
ORDER BY allowlist_status;
*/