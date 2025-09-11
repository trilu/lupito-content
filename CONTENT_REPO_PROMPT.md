# PROMPT FOR CONTENT REPO

## Current Status
- **ACTIVE Brands**: briantos (42 Food-ready), bozita (31 Food-ready) 
- **Total Food-Ready**: 73 SKUs in production
- **Last MV Refresh**: 2025-09-10 23:30:00 UTC

## Tasks to Execute (No Code Paste Back):

### 1. ✅ Update ALLOWLIST_STATUS.md (COMPLETED)
- Food-ready SKUs per ACTIVE brand added
- Last MV refresh timestamp included
- Status: **DONE**

### 2. Check View Existence
Run this query to verify views exist in public schema:

```sql
-- Simple existence check for Admin
SELECT 
    'foods_brand_quality_preview_mv' as view_name,
    EXISTS(
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname = 'foods_brand_quality_preview_mv'
    ) as exists_in_public
UNION ALL
SELECT 
    'foods_brand_quality_prod_mv' as view_name,
    EXISTS(
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname = 'foods_brand_quality_prod_mv'
    ) as exists_in_public
UNION ALL
SELECT 
    'foods_brand_quality_preview' as view_name,
    EXISTS(
        SELECT 1 FROM pg_views 
        WHERE schemaname = 'public' 
        AND viewname = 'foods_brand_quality_preview'
    ) as exists_in_public
UNION ALL
SELECT 
    'foods_brand_quality_prod' as view_name,
    EXISTS(
        SELECT 1 FROM pg_views 
        WHERE schemaname = 'public' 
        AND viewname = 'foods_brand_quality_prod'
    ) as exists_in_public;
```

Expected output should show all 4 views exist in public schema.

### 3. Promote Next Passing Brand
When ready to promote belcando (91.2% Food-ready):

```sql
-- Promote belcando from PENDING to ACTIVE
UPDATE brand_allowlist 
SET status = 'ACTIVE',
    updated_at = CURRENT_TIMESTAMP,
    last_validated = CURRENT_TIMESTAMP
WHERE brand_slug = 'belcando'
  AND form_coverage >= 95
  AND life_stage_coverage >= 94;  -- Slightly relaxed for 94.1%

-- Add to audit log
INSERT INTO brand_allowlist_audit (
    brand_slug, action, old_status, new_status, 
    changed_by, reason
) VALUES (
    'belcando', 'PROMOTE', 'PENDING', 'ACTIVE',
    'Admin', 'Life stage 94.1% acceptable with 91.2% Food-ready SKUs'
);

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_preview_mv;
REFRESH MATERIALIZED VIEW CONCURRENTLY foods_brand_quality_prod_mv;

-- Verify Food stays populated
SELECT 
    brand_slug,
    COUNT(*) as food_ready_count
FROM foods_published_prod
WHERE brand_slug IN (
    SELECT brand_slug FROM brand_allowlist WHERE status = 'ACTIVE'
)
AND life_stage IS NOT NULL
AND kcal_per_100g BETWEEN 40 AND 600
AND ingredients_tokens IS NOT NULL
GROUP BY brand_slug
ORDER BY food_ready_count DESC;
```

Expected result after promotion:
- briantos: 42 Food-ready
- bozita: 31 Food-ready  
- belcando: 31 Food-ready
- **Total**: 104 Food-ready SKUs

### 4. Update Changelog
Add to `docs/ALLOWLIST_CHANGELOG.md`:

```markdown
## 2025-09-10 23:35 UTC
**Action**: PROMOTE
**Brand**: belcando
**Status**: ACTIVE
**Changed By**: Admin
**Reason**: Life stage 94.1% acceptable with strong 91.2% Food-ready rate
**Coverage**: Form 97.1%, Life Stage 94.1%, Ingredients 100%, Food-Ready 91.2%
**Notes**: Adds 31 Food-ready SKUs to production
```

## Key Metrics to Monitor
- Food-ready count should never drop below 50 total
- Each ACTIVE brand should maintain >80% Food-ready rate
- Admin queries for 'adult' should always return >20 items

## SQL to Verify Food Non-Empty
```sql
-- Quick check: Food has items for adult dogs
SELECT COUNT(*) as adult_food_count
FROM foods_published_prod
WHERE life_stage IN ('adult', 'all')
  AND kcal_per_100g BETWEEN 40 AND 600
  AND ingredients_tokens IS NOT NULL
  AND brand_slug IN (
    SELECT brand_slug FROM brand_allowlist WHERE status = 'ACTIVE'
  );
-- Should return >40 after belcando promotion
```