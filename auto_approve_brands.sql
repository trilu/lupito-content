-- Auto-approve brands with high-quality products
-- This will add 192 brands to brand_allowlist, which will automatically
-- make their 4,311 high-quality products ACTIVE in foods_published_preview

-- STEP 1: See current brand allowlist count
SELECT COUNT(*) as current_allowlist_brands FROM brand_allowlist;

-- STEP 2: Preview the brands that will be added
-- These are brands with products that have images + ingredients + nutrients
WITH quality_pending_brands AS (
  SELECT DISTINCT brand_slug
  FROM foods_published_preview
  WHERE allowlist_status = 'PENDING'
    AND image_url IS NOT NULL
    AND ingredients_tokens IS NOT NULL
    AND (protein_percent IS NOT NULL OR fat_percent IS NOT NULL OR kcal_per_100g IS NOT NULL)
    AND brand_slug IS NOT NULL  -- Filter out NULL brand_slugs
),
brands_to_add AS (
  SELECT qpb.brand_slug
  FROM quality_pending_brands qpb
  LEFT JOIN brand_allowlist ba ON qpb.brand_slug = ba.brand_slug
  WHERE ba.brand_slug IS NULL
)
SELECT COUNT(*) as brands_to_add FROM brands_to_add;

-- STEP 3: Execute the brand additions (UNCOMMENT TO RUN):
/*
WITH quality_pending_brands AS (
  SELECT DISTINCT brand_slug
  FROM foods_published_preview
  WHERE allowlist_status = 'PENDING'
    AND image_url IS NOT NULL
    AND ingredients_tokens IS NOT NULL
    AND (protein_percent IS NOT NULL OR fat_percent IS NOT NULL OR kcal_per_100g IS NOT NULL)
    AND brand_slug IS NOT NULL  -- Filter out NULL brand_slugs
),
brands_to_add AS (
  SELECT qpb.brand_slug
  FROM quality_pending_brands qpb
  LEFT JOIN brand_allowlist ba ON qpb.brand_slug = ba.brand_slug
  WHERE ba.brand_slug IS NULL
)
INSERT INTO brand_allowlist (brand_slug, status, created_at, updated_at, notes)
SELECT
  brand_slug,
  'ACTIVE',
  NOW(),
  NOW(),
  'Auto-approved: quality products (images + ingredients + nutrients)'
FROM brands_to_add
WHERE brand_slug IS NOT NULL;  -- Double safety check
*/

-- STEP 4: After execution, verify the results:
/*
-- Check new brand count
SELECT COUNT(*) as total_allowlist_brands FROM brand_allowlist;

-- Check updated product status distribution
SELECT allowlist_status, COUNT(*) as count
FROM foods_published_preview
GROUP BY allowlist_status
ORDER BY allowlist_status;

-- Verify we achieved the expected numbers:
-- Expected: ~7,430 ACTIVE (3,119 + 4,311) and ~1,909 PENDING
*/