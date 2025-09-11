-- ============================================
-- SCHEMA MIGRATION: Nutrition & Ingredients Columns
-- Execute this to add missing columns to foods_canonical
-- ============================================

-- Start transaction for safety
BEGIN;

-- ============================================
-- Add columns to foods_canonical
-- ============================================

-- Ingredients tracking columns
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_raw TEXT;

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_source TEXT 
    CHECK (ingredients_source IN ('label', 'pdf', 'site', 'manual') OR ingredients_source IS NULL);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_parsed_at TIMESTAMPTZ;

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ingredients_language TEXT DEFAULT 'en';

-- Macronutrient columns
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS fiber_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS ash_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS moisture_percent NUMERIC(5,2);

ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS macros_source TEXT 
    CHECK (macros_source IN ('label', 'pdf', 'site', 'derived') OR macros_source IS NULL);

-- Kcal source tracking
ALTER TABLE foods_canonical 
ADD COLUMN IF NOT EXISTS kcal_source TEXT 
    CHECK (kcal_source IN ('label', 'pdf', 'site', 'derived') OR kcal_source IS NULL);

-- ============================================
-- Create performance indexes
-- ============================================

CREATE INDEX IF NOT EXISTS idx_foods_canonical_ingredients_source 
    ON foods_canonical(ingredients_source) 
    WHERE ingredients_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_macros_source 
    ON foods_canonical(macros_source) 
    WHERE macros_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_kcal_source 
    ON foods_canonical(kcal_source) 
    WHERE kcal_source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_ingredients 
    ON foods_canonical(brand_slug) 
    WHERE ingredients_tokens IS NULL OR jsonb_array_length(ingredients_tokens) = 0;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_macros 
    ON foods_canonical(brand_slug) 
    WHERE protein_percent IS NULL OR fat_percent IS NULL;

CREATE INDEX IF NOT EXISTS idx_foods_canonical_missing_fiber 
    ON foods_canonical(brand_slug) 
    WHERE fiber_percent IS NULL;

-- Commit the transaction
COMMIT;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRATION COMPLETE!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Added nutrition columns to foods_canonical';
    RAISE NOTICE 'Views will automatically show new columns';
    RAISE NOTICE '========================================';
END $$;