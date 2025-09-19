-- Fix IAMS Brand Anomaly: 155444 → IAMS
-- This fixes 11 products incorrectly labeled as brand "155444"
-- All product names clearly show they are IAMS products

-- STEP 1: Verify the anomaly
SELECT
  'Products with brand 155444' as check_type,
  COUNT(*) as count
FROM foods_canonical
WHERE brand = '155444';

-- Show sample product names to confirm they're IAMS
SELECT
  brand,
  brand_slug,
  product_name
FROM foods_canonical
WHERE brand = '155444'
LIMIT 5;

-- STEP 2: Check IAMS allowlist status
SELECT
  'IAMS allowlist status' as check_type,
  brand_slug,
  status
FROM brand_allowlist
WHERE brand_slug = 'iams';

-- STEP 3: Check for potential conflicts
-- Verify no existing products with same product_keys
WITH anomaly_keys AS (
  SELECT product_key
  FROM foods_canonical
  WHERE brand = '155444'
),
potential_conflicts AS (
  SELECT fc.product_key, fc.brand, fc.brand_slug
  FROM foods_canonical fc
  JOIN anomaly_keys ak ON fc.product_key = ak.product_key
  WHERE fc.brand != '155444'
)
SELECT
  'Potential conflicts' as check_type,
  COUNT(*) as count
FROM potential_conflicts;

-- STEP 4: Preview the fix
SELECT
  'Before fix' as status,
  brand as current_brand,
  brand_slug as current_brand_slug,
  'IAMS' as new_brand,
  'iams' as new_brand_slug,
  product_name
FROM foods_canonical
WHERE brand = '155444'
LIMIT 3;

-- STEP 5: Execute the fix (UNCOMMENT TO RUN)
/*
UPDATE foods_canonical
SET
  brand = 'IAMS',
  brand_slug = 'iams'
WHERE brand = '155444' AND brand_slug IS NULL;
*/

-- STEP 6: Verify the fix (UNCOMMENT TO RUN AFTER EXECUTION)
/*
-- Check update success
SELECT
  'Updated products' as check_type,
  COUNT(*) as count
FROM foods_canonical
WHERE brand = 'IAMS' AND brand_slug = 'iams'
  AND product_name LIKE '%IAMS Advanced Nutrition%';

-- Check new publication status
SELECT
  allowlist_status,
  COUNT(*) as count
FROM foods_published_preview
WHERE brand = 'IAMS' AND brand_slug = 'iams'
  AND product_name LIKE '%IAMS Advanced Nutrition%'
GROUP BY allowlist_status;

-- Overall impact on PENDING count
SELECT
  'PENDING products after fix' as status,
  COUNT(*) as count
FROM foods_published_preview
WHERE allowlist_status = 'PENDING';
*/

-- Expected Results:
-- Before: 11 products with brand="155444", brand_slug=NULL, status=PENDING
-- After: 11 products with brand="IAMS", brand_slug="iams", status=ACTIVE
-- Impact: PENDING count reduces from 506 to 495 (-11)