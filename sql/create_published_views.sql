-- SQL Script 2: Published Views (prod + preview)
-- Fixed version that doesn't assume column names
-- Adapt column list based on actual foods_canonical structure

-- Create foods_published_prod view (ACTIVE brands only)
CREATE OR REPLACE VIEW foods_published_prod AS
SELECT 
    -- Core identification fields
    f.brand,
    f.product_name,
    f.brand_slug,
    f.name_slug,
    f.product_key,
    
    -- Product attributes (check if these exist in your table)
    f.form,
    f.life_stage,
    f.kcal_per_100g,
    -- f.price_per_kg_eur,  -- Uncomment if this column exists
    -- f.price_bucket,      -- Uncomment if this column exists
    
    -- Brand family fields (check if these exist in your table)
    -- f.brand_family,      -- Uncomment if this column exists
    -- f.series,            -- Uncomment if this column exists
    
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
    
    -- Timestamps (if they exist)
    f.created_at,
    f.updated_at
FROM foods_canonical f
INNER JOIN brand_allowlist a ON f.brand_slug = a.brand_slug
WHERE a.status = 'ACTIVE';

-- Create foods_published_preview view (ACTIVE + PENDING)
CREATE OR REPLACE VIEW foods_published_preview AS
SELECT 
    -- Core identification fields
    f.brand,
    f.product_name,
    f.brand_slug,
    f.name_slug,
    f.product_key,
    
    -- Product attributes (check if these exist in your table)
    f.form,
    f.life_stage,
    f.kcal_per_100g,
    -- f.price_per_kg_eur,  -- Uncomment if this column exists
    -- f.price_bucket,      -- Uncomment if this column exists
    
    -- Brand family fields (check if these exist in your table)
    -- f.brand_family,      -- Uncomment if this column exists
    -- f.series,            -- Uncomment if this column exists
    
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
    
    -- Timestamps (if they exist)
    f.created_at,
    f.updated_at
FROM foods_canonical f
INNER JOIN brand_allowlist a ON f.brand_slug = a.brand_slug
WHERE a.status IN ('ACTIVE', 'PENDING');

-- Create indexes on underlying table for performance
CREATE INDEX IF NOT EXISTS idx_foods_canonical_brand_slug ON foods_canonical (brand_slug);
CREATE INDEX IF NOT EXISTS idx_foods_canonical_brand_family ON foods_canonical (brand_family) 
    WHERE brand_family IS NOT NULL;
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