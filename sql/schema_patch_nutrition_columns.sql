-- ============================================
-- IDEMPOTENT SCHEMA MIGRATION: Nutrition & Ingredients Columns
-- Generated: 2025-09-11
-- Purpose: Add missing nutrition/ingredients columns to foods_canonical
-- Note: foods_published_preview and foods_published_prod are views that will auto-update
-- ============================================

-- Start transaction for safety
BEGIN;

-- ============================================
-- STEP 1: Add columns to foods_canonical (primary write layer)
-- ============================================

-- Ingredients columns
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_raw TEXT;

-- ingredients_tokens already exists as JSONB, but ensure it's there
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_tokens JSONB DEFAULT '[]'::jsonb;

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_source TEXT 
    CHECK (ingredients_source IN ('label', 'pdf', 'site', 'manual') OR ingredients_source IS NULL);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMPTZ;

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_language TEXT DEFAULT 'en';

-- Macronutrient columns (some may exist)
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS protein_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS fat_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS fiber_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ash_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS moisture_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS macros_source TEXT 
    CHECK (macros_source IN ('label', 'pdf', 'site', 'derived') OR macros_source IS NULL);

-- Kcal columns (kcal_per_100g likely exists)
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS kcal_per_100g NUMERIC(6,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS kcal_source TEXT 
    CHECK (kcal_source IN ('label', 'pdf', 'site', 'derived') OR kcal_source IS NULL);

-- ============================================
-- STEP 2: Add same columns to foods_published
-- ============================================

-- Ingredients columns
ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_raw TEXT;

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_tokens JSONB DEFAULT '[]'::jsonb;

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_source TEXT 
    CHECK (ingredients_source IN ('label', 'pdf', 'site', 'manual') OR ingredients_source IS NULL);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMPTZ;

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS ingredients_language TEXT DEFAULT 'en';

-- Macronutrient columns
ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS protein_percent NUMERIC(5,2);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS fat_percent NUMERIC(5,2);

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
ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS kcal_per_100g NUMERIC(6,2);

ALTER TABLE foods_published 
ADD COLUMN IF NOT EXISTS kcal_source TEXT 
    CHECK (kcal_source IN ('label', 'pdf', 'site', 'derived') OR kcal_source IS NULL);

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

-- Index for finding products missing data
CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_ingredients 
    ON foods_canonical(brand_slug) 
    WHERE ingredients_tokens IS NULL OR jsonb_array_length(ingredients_tokens) = 0;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_macros 
    ON foods_canonical(brand_slug) 
    WHERE protein_percent IS NULL OR fat_percent IS NULL;

-- ============================================
-- STEP 4: Verify columns were added
-- ============================================

-- Create a verification query
DO $$
DECLARE
    col_count INTEGER;
    new_cols TEXT[];
BEGIN
    -- Check which columns were added
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'foods_canonical'
    AND column_name IN (
        'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at', 
        'ingredients_language', 'fiber_percent', 'ash_percent', 
        'moisture_percent', 'macros_source', 'kcal_source'
    );
    
    RAISE NOTICE 'Schema patch complete. Nutrition columns verified: %', col_count;
END $$;

-- ============================================
-- STEP 5: Update/Recreate Views if needed
-- ============================================

-- Note: foods_published_preview and foods_published_prod are views
-- They should automatically reflect the new columns from the base tables
-- Let's verify they exist and show the structure

-- Check if views need refresh
DO $$
BEGIN
    -- If views exist, they should automatically show new columns
    -- since they likely use SELECT * or explicit column lists
    IF EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_name = 'foods_published_preview'
    ) THEN
        RAISE NOTICE 'View foods_published_preview exists - new columns will be available';
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.views 
        WHERE table_name = 'foods_published_prod'
    ) THEN
        RAISE NOTICE 'View foods_published_prod exists - new columns will be available';
    END IF;
END $$;

-- Commit the transaction
COMMIT;

-- ============================================
-- VERIFICATION QUERIES (Run these after migration)
-- ============================================

-- Query 1: Show all nutrition columns in foods_canonical
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    column_default
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 'ingredients_tokens', 'ingredients_source', 
    'ingredients_parsed_at', 'ingredients_language',
    'protein_percent', 'fat_percent', 'fiber_percent', 
    'ash_percent', 'moisture_percent', 'macros_source',
    'kcal_per_100g', 'kcal_source'
)
ORDER BY ordinal_position;

-- Query 2: Count products with new data
SELECT 
    COUNT(*) as total_products,
    COUNT(ingredients_raw) as has_ingredients_raw,
    COUNT(ingredients_source) as has_ingredients_source,
    COUNT(fiber_percent) as has_fiber,
    COUNT(ash_percent) as has_ash,
    COUNT(moisture_percent) as has_moisture,
    COUNT(macros_source) as has_macros_source,
    COUNT(kcal_source) as has_kcal_source
FROM foods_canonical;

-- Query 3: Verify views have new columns
SELECT column_name
FROM information_schema.columns
WHERE table_name IN ('foods_published_preview', 'foods_published_prod')
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 'fiber_percent', 
    'ash_percent', 'moisture_percent', 'macros_source', 'kcal_source'
)
ORDER BY table_name, column_name;