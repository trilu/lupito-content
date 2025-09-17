-- Auto-approve products meeting quality criteria
-- This will approve products that have:
-- 1. Images (image_url IS NOT NULL)
-- 2. Ingredients (ingredients_tokens IS NOT NULL)
-- 3. Nutrient data (any of: protein_percent, fat_percent, kcal_per_100g)

-- STEP 1: Preview query to see what will be updated
SELECT COUNT(*) as products_to_approve
FROM foods_published_preview
WHERE allowlist_status = 'PENDING'
  AND image_url IS NOT NULL
  AND ingredients_tokens IS NOT NULL
  AND (protein_percent IS NOT NULL OR fat_percent IS NOT NULL OR kcal_per_100g IS NOT NULL);

-- STEP 2: See current status before update
SELECT allowlist_status, COUNT(*) as count
FROM foods_published_preview
GROUP BY allowlist_status;

-- STEP 3: Execute the update (UNCOMMENT TO RUN):
/*
UPDATE foods_published_preview
SET
  allowlist_status = 'ACTIVE',
  allowlist_updated_at = NOW()
WHERE allowlist_status = 'PENDING'
  AND image_url IS NOT NULL
  AND ingredients_tokens IS NOT NULL
  AND (protein_percent IS NOT NULL OR fat_percent IS NOT NULL OR kcal_per_100g IS NOT NULL);
*/

-- STEP 4: After update, verify results:
/*
SELECT
  allowlist_status,
  COUNT(*) as count
FROM foods_published_preview
GROUP BY allowlist_status
ORDER BY allowlist_status;
*/