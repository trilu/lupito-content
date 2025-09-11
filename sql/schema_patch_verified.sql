-- ============================================
-- VERIFIED SCHEMA MIGRATION: Nutrition & Ingredients Columns
-- Generated: 2025-09-11
-- Based on actual Supabase schema check
-- ============================================

-- IMPORTANT NOTES:
-- 1. foods_canonical: Primary table with 25 columns
-- 2. foods_published: Secondary table with 24 columns (missing kcal_per_100g_final)
-- 3. foods_published_preview: View with 27 columns (includes allowlist_status, allowlist_updated_at)
-- 4. foods_published_prod: View with 26 columns (includes allowlist_status)
-- 5. manufacturer_harvest_staging: Already has nutrition columns!

-- Start transaction for safety
BEGIN;

-- ============================================
-- STEP 1: Add columns to foods_canonical (primary table)
-- ============================================

-- Ingredients tracking columns
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_raw TEXT;

-- ingredients_tokens already exists as JSONB, confirmed present

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_source TEXT 
    CHECK (ingredients_source IN ('label', 'pdf', 'site', 'manual') OR ingredients_source IS NULL);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMPTZ;

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_language TEXT DEFAULT 'en';

-- Macronutrient columns
-- protein_percent already exists (confirmed)
-- fat_percent already exists (confirmed)

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS fiber_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ash_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS moisture_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS macros_source TEXT 
    CHECK (macros_source IN ('label', 'pdf', 'site', 'derived') OR macros_source IS NULL);

-- Kcal columns
-- kcal_per_100g already exists (confirmed)
-- kcal_is_estimated already exists (confirmed)
-- kcal_per_100g_final already exists (confirmed)

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS kcal_source TEXT 
    CHECK (kcal_source IN ('label', 'pdf', 'site', 'derived') OR kcal_source IS NULL);

-- ============================================
-- STEP 2: Add same columns to foods_published
-- ============================================

-- Ingredients tracking columns
ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_raw TEXT;

-- ingredients_tokens already exists as JSONB

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_source TEXT 
    CHECK (ingredients_source IN ('label', 'pdf', 'site', 'manual') OR ingredients_source IS NULL);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMPTZ;

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_language TEXT DEFAULT 'en';

-- Macronutrient columns
-- protein_percent already exists
-- fat_percent already exists

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS fiber_percent NUMERIC(5,2);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ash_percent NUMERIC(5,2);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS moisture_percent NUMERIC(5,2);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS macros_source TEXT 
    CHECK (macros_source IN ('label', 'pdf', 'site', 'derived') OR macros_source IS NULL);

-- Kcal columns
-- kcal_per_100g already exists
-- kcal_is_estimated already exists

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS kcal_source TEXT 
    CHECK (kcal_source IN ('label', 'pdf', 'site', 'derived') OR kcal_source IS NULL);

-- Add the missing kcal_per_100g_final to match foods_canonical
ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS kcal_per_100g_final NUMERIC(6,2);

-- ============================================
-- STEP 3: Create indexes for performance
-- ============================================

-- Index on source columns for filtering
CREATE INDEX IF NOT EXISTS idx_foods_canonical_ingredients_source 
    ON foods_canonical(ingredients_source) 
    WHERE ingredients_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_macros_source 
    ON foods_canonical(macros_source) 
    WHERE macros_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_kcal_source 
    ON foods_canonical(kcal_source) 
    WHERE kcal_source IS NOT NULL;

-- Same indexes for foods_published
CREATE INDEX IF NOT EXISTS idx_foods_published_ingredients_source 
    ON foods_published(ingredients_source) 
    WHERE ingredients_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_published_macros_source 
    ON foods_published(macros_source) 
    WHERE macros_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_published_kcal_source 
    ON foods_published(kcal_source) 
    WHERE kcal_source IS NOT NULL;

-- Index for finding products missing data
CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_ingredients 
    ON foods_canonical(brand_slug) 
    WHERE ingredients_tokens IS NULL OR jsonb_array_length(ingredients_tokens) = 0;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_macros 
    ON foods_canonical(brand_slug) 
    WHERE protein_percent IS NULL OR fat_percent IS NULL;

-- ============================================
-- STEP 4: Note about manufacturer_harvest_staging
-- ============================================

-- manufacturer_harvest_staging already has these columns:
-- ✅ ingredients_raw TEXT
-- ✅ ingredients_tokens TEXT[]
-- ✅ protein_percent DECIMAL
-- ✅ fat_percent DECIMAL
-- ✅ fibre_percent DECIMAL (note: different spelling)
-- ✅ ash_percent DECIMAL
-- ✅ moisture_percent DECIMAL
-- ✅ kcal_per_100g INTEGER

-- No changes needed to manufacturer_harvest_staging

-- ============================================
-- STEP 5: Refresh any materialized views
-- ============================================

-- If there are any materialized views, refresh them
-- (Views will automatically show new columns)

DO $$
BEGIN
    -- Check if any materialized views need refresh
    IF EXISTS (
        SELECT 1 FROM pg_matviews 
        WHERE schemaname = 'public' 
        AND matviewname LIKE 'foods%'
    ) THEN
        -- Refresh materialized views if they exist
        EXECUTE 'REFRESH MATERIALIZED VIEW CONCURRENTLY IF EXISTS foods_quality_view';
        RAISE NOTICE 'Materialized views refreshed (if any exist)';
    END IF;
END $$;

-- Commit the transaction
COMMIT;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- 1. Verify new columns in foods_canonical
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
    'ingredients_language', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
)
ORDER BY column_name;

-- 2. Verify new columns in foods_published
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'foods_published'
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
    'ingredients_language', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source', 'kcal_per_100g_final'
)
ORDER BY column_name;

-- 3. Check if views can see new columns
SELECT 
    table_name as view_name,
    column_name
FROM information_schema.columns
WHERE table_name IN ('foods_published_preview', 'foods_published_prod')
AND column_name IN ('fiber_percent', 'ash_percent', 'moisture_percent')
ORDER BY table_name, column_name;

-- 4. Summary of what was added
WITH new_cols AS (
    SELECT 
        'foods_canonical' as table_name,
        COUNT(*) as columns_added
    FROM information_schema.columns
    WHERE table_name = 'foods_canonical'
    AND column_name IN (
        'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
        'ingredients_language', 'fiber_percent', 'ash_percent', 
        'moisture_percent', 'macros_source', 'kcal_source'
    )
    UNION ALL
    SELECT 
        'foods_published' as table_name,
        COUNT(*) as columns_added
    FROM information_schema.columns
    WHERE table_name = 'foods_published'
    AND column_name IN (
        'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
        'ingredients_language', 'fiber_percent', 'ash_percent', 
        'moisture_percent', 'macros_source', 'kcal_source', 'kcal_per_100g_final'
    )
)
SELECT * FROM new_cols;