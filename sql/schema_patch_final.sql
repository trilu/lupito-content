-- ============================================
-- FINAL SCHEMA MIGRATION: Nutrition & Ingredients Columns
-- Generated: 2025-09-11
-- Verified Structure:
--   - foods_canonical: BASE TABLE (write layer) 
--   - foods_published: VIEW (reads from foods_canonical)
--   - foods_published_preview: VIEW 
--   - foods_published_prod: VIEW
-- ============================================

-- IMPORTANT: Only modify foods_canonical (base table)
-- Views will automatically inherit the new columns

-- Start transaction for safety
BEGIN;

-- ============================================
-- STEP 1: Add columns to foods_canonical (the only actual table)
-- ============================================

-- Ingredients tracking columns
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_raw TEXT;

-- ingredients_tokens already exists as JSONB (confirmed)

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_source TEXT 
    CHECK (ingredients_source IN ('label', 'pdf', 'site', 'manual') OR ingredients_source IS NULL);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMPTZ;

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_language TEXT DEFAULT 'en';

-- Macronutrient columns
-- protein_percent already exists (confirmed: NUMERIC)
-- fat_percent already exists (confirmed: NUMERIC)

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
-- kcal_per_100g already exists (confirmed: NUMERIC)
-- kcal_is_estimated already exists (confirmed: BOOLEAN)
-- kcal_per_100g_final already exists (confirmed: NUMERIC)

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS kcal_source TEXT 
    CHECK (kcal_source IN ('label', 'pdf', 'site', 'derived') OR kcal_source IS NULL);

-- ============================================
-- STEP 2: Create performance indexes
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

-- Index for finding products missing data
CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_ingredients 
    ON foods_canonical(brand_slug) 
    WHERE ingredients_tokens IS NULL OR jsonb_array_length(ingredients_tokens) = 0;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_macros 
    ON foods_canonical(brand_slug) 
    WHERE protein_percent IS NULL OR fat_percent IS NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_fiber 
    ON foods_canonical(brand_slug) 
    WHERE fiber_percent IS NULL;

-- ============================================
-- STEP 3: Recreate/Refresh Views (if needed)
-- ============================================

-- The views should automatically show the new columns
-- But we can force a refresh to ensure they're visible

-- Option 1: If views need explicit column listing, recreate them
-- (Uncomment and modify if your views don't automatically show new columns)

/*
-- Example view recreation (adjust SELECT list as needed):
CREATE OR REPLACE VIEW foods_published AS
SELECT 
    product_key,
    brand,
    brand_slug,
    product_name,
    name_slug,
    form,
    life_stage,
    -- Existing nutrition columns
    protein_percent,
    fat_percent,
    kcal_per_100g,
    kcal_is_estimated,
    -- NEW nutrition columns
    fiber_percent,
    ash_percent,
    moisture_percent,
    macros_source,
    kcal_source,
    -- Ingredients columns
    ingredients_tokens,
    ingredients_raw,      -- NEW
    ingredients_source,   -- NEW
    ingredients_parsed_at, -- NEW
    ingredients_language,  -- NEW
    -- Other existing columns
    has_chicken,
    has_poultry,
    primary_protein,
    price_per_kg,
    price_bucket,
    quality_score,
    image_url,
    product_url,
    available_countries,
    source,
    sources,
    updated_at
FROM foods_canonical;
*/

-- ============================================
-- STEP 4: Grant permissions (if needed)
-- ============================================

-- Ensure proper permissions on new columns
-- (Adjust roles as needed for your setup)

/*
GRANT SELECT ON foods_canonical TO authenticated;
GRANT SELECT ON foods_canonical TO anon;
GRANT SELECT ON foods_canonical TO service_role;
*/

-- Commit the transaction
COMMIT;

-- ============================================
-- VERIFICATION QUERIES (Run after migration)
-- ============================================

-- 1. Verify new columns were added to foods_canonical
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 
    'ingredients_source', 
    'ingredients_parsed_at',
    'ingredients_language', 
    'fiber_percent', 
    'ash_percent', 
    'moisture_percent', 
    'macros_source', 
    'kcal_source'
)
ORDER BY column_name;

-- 2. Count how many columns were successfully added
SELECT 
    COUNT(*) as new_columns_added,
    COUNT(*) FILTER (WHERE column_name LIKE 'ingredients_%') as ingredients_columns,
    COUNT(*) FILTER (WHERE column_name LIKE '%_percent') as nutrition_columns,
    COUNT(*) FILTER (WHERE column_name LIKE '%_source') as source_columns
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
    'ingredients_language', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
);

-- 3. Check if views can see the new columns
-- (Views should automatically inherit from base table)
SELECT 
    table_name as view_name,
    COUNT(*) as visible_new_columns
FROM information_schema.columns
WHERE table_name IN ('foods_published', 'foods_published_preview', 'foods_published_prod')
AND column_name IN (
    'ingredients_raw', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
)
GROUP BY table_name
ORDER BY table_name;

-- 4. Test that we can query the new columns through views
SELECT 
    product_key,
    ingredients_raw,
    fiber_percent,
    ash_percent,
    moisture_percent,
    macros_source,
    kcal_source
FROM foods_published
LIMIT 1;

-- 5. Check indexes were created
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE tablename = 'foods_canonical'
AND indexname LIKE '%ingredients%' 
   OR indexname LIKE '%macros%' 
   OR indexname LIKE '%kcal%'
   OR indexname LIKE '%fiber%'
ORDER BY indexname;

-- ============================================
-- POST-MIGRATION REPORT
-- ============================================

-- Summary of what was added
WITH migration_summary AS (
    SELECT 
        'Total new columns' as metric,
        COUNT(*) as value
    FROM information_schema.columns
    WHERE table_name = 'foods_canonical'
    AND column_name IN (
        'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
        'ingredients_language', 'fiber_percent', 'ash_percent', 
        'moisture_percent', 'macros_source', 'kcal_source'
    )
    UNION ALL
    SELECT 
        'New indexes created',
        COUNT(*)
    FROM pg_indexes
    WHERE tablename = 'foods_canonical'
    AND (indexname LIKE 'idx_foods_canonical_%source' 
         OR indexname LIKE 'idx_foods_canonical_missing_%')
    AND indexname IN (
        'idx_foods_canonical_ingredients_source',
        'idx_foods_canonical_macros_source',
        'idx_foods_canonical_kcal_source',
        'idx_foods_canonical_missing_ingredients',
        'idx_foods_canonical_missing_macros',
        'idx_foods_canonical_missing_fiber'
    )
)
SELECT * FROM migration_summary;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'foods_canonical'
    AND column_name IN (
        'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
        'ingredients_language', 'fiber_percent', 'ash_percent', 
        'moisture_percent', 'macros_source', 'kcal_source'
    );
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION COMPLETE!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Added % new columns to foods_canonical', col_count;
    RAISE NOTICE 'Views will automatically show new columns';
    RAISE NOTICE '========================================';
END $$;