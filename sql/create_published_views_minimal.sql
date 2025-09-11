-- SQL Script 2: Published Views (Minimal Version)
-- This version only includes core columns that should exist in foods_canonical
-- Add more columns as needed based on your actual table structure

-- First, let's check what columns actually exist (run this query first to see the structure)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'foods_canonical' 
-- ORDER BY ordinal_position;

-- Create foods_published_prod view (ACTIVE brands only)
CREATE OR REPLACE VIEW foods_published_prod AS
SELECT 
    -- Core identification fields (these should definitely exist)
    f.brand,
    f.product_name,
    f.brand_slug,
    f.name_slug,
    f.product_key,
    
    -- Product attributes (comment out any that don't exist)
    f.form,
    f.life_stage,
    f.kcal_per_100g,
    
    -- Cast arrays to jsonb under original names
    CASE 
        WHEN f.ingredients_tokens IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(f.ingredients_tokens::jsonb) = 'array' THEN f.ingredients_tokens::jsonb
        ELSE '[]'::jsonb
    END AS ingredients_tokens,
    
    CASE 
        WHEN f.available_countries IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(f.available_countries::jsonb) = 'array' THEN f.available_countries::jsonb
        ELSE '[]'::jsonb
    END AS available_countries,
    
    CASE 
        WHEN f.sources IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(f.sources::jsonb) = 'array' THEN f.sources::jsonb
        ELSE '[]'::jsonb
    END AS sources,
    
    -- Include allowlist status
    a.status AS allowlist_status,
    
    -- Timestamps (comment out if they don't exist)
    f.created_at,
    f.updated_at
FROM foods_canonical f
INNER JOIN brand_allowlist a ON f.brand_slug = a.brand_slug
WHERE a.status = 'ACTIVE';

-- Create foods_published_preview view (ACTIVE + PENDING)
CREATE OR REPLACE VIEW foods_published_preview AS
SELECT 
    -- Core identification fields (these should definitely exist)
    f.brand,
    f.product_name,
    f.brand_slug,
    f.name_slug,
    f.product_key,
    
    -- Product attributes (comment out any that don't exist)
    f.form,
    f.life_stage,
    f.kcal_per_100g,
    
    -- Cast arrays to jsonb under original names
    CASE 
        WHEN f.ingredients_tokens IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(f.ingredients_tokens::jsonb) = 'array' THEN f.ingredients_tokens::jsonb
        ELSE '[]'::jsonb
    END AS ingredients_tokens,
    
    CASE 
        WHEN f.available_countries IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(f.available_countries::jsonb) = 'array' THEN f.available_countries::jsonb
        ELSE '[]'::jsonb
    END AS available_countries,
    
    CASE 
        WHEN f.sources IS NULL THEN '[]'::jsonb
        WHEN jsonb_typeof(f.sources::jsonb) = 'array' THEN f.sources::jsonb
        ELSE '[]'::jsonb
    END AS sources,
    
    -- Include allowlist status
    a.status AS allowlist_status,
    
    -- Timestamps (comment out if they don't exist)
    f.created_at,
    f.updated_at
FROM foods_canonical f
INNER JOIN brand_allowlist a ON f.brand_slug = a.brand_slug
WHERE a.status IN ('ACTIVE', 'PENDING');

-- Create indexes on underlying table for performance
CREATE INDEX IF NOT EXISTS idx_foods_canonical_brand_slug ON foods_canonical (brand_slug);
CREATE INDEX IF NOT EXISTS idx_foods_canonical_life_stage ON foods_canonical (life_stage) 
    WHERE life_stage IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_foods_canonical_form ON foods_canonical (form) 
    WHERE form IS NOT NULL;

-- Grant permissions (uncomment and adjust roles as needed)
-- GRANT SELECT ON foods_published_prod TO anon;
-- GRANT SELECT ON foods_published_prod TO authenticated;
-- GRANT SELECT ON foods_published_prod TO service_role;
-- GRANT SELECT ON foods_published_preview TO anon;
-- GRANT SELECT ON foods_published_preview TO authenticated;
-- GRANT SELECT ON foods_published_preview TO service_role;