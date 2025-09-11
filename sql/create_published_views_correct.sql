-- SQL Script 2: Published Views (Corrected for actual table structure)
-- Based on actual foods_canonical columns in Supabase

-- Create foods_published_prod view (ACTIVE brands only)
CREATE OR REPLACE VIEW foods_published_prod AS
SELECT 
    -- Core identification fields
    f.brand,
    f.product_name,
    f.brand_slug,
    f.name_slug,
    f.product_key,
    
    -- Product attributes
    f.form,
    f.life_stage,
    f.primary_protein,
    
    -- Nutrition data
    f.kcal_per_100g,
    f.kcal_per_100g_final,
    f.kcal_is_estimated,
    f.protein_percent,
    f.fat_percent,
    
    -- Price data
    f.price_per_kg,
    f.price_bucket,
    
    -- Product details
    f.has_chicken,
    f.has_poultry,
    f.quality_score,
    
    -- URLs
    f.product_url,
    f.image_url,
    
    -- Source info
    f.source,
    
    -- Cast arrays to jsonb under original names (they're already arrays)
    f.ingredients_tokens::jsonb AS ingredients_tokens,
    f.available_countries::jsonb AS available_countries,
    f.sources::jsonb AS sources,
    
    -- Include allowlist status
    a.status AS allowlist_status,
    
    -- Timestamp
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
    
    -- Product attributes
    f.form,
    f.life_stage,
    f.primary_protein,
    
    -- Nutrition data
    f.kcal_per_100g,
    f.kcal_per_100g_final,
    f.kcal_is_estimated,
    f.protein_percent,
    f.fat_percent,
    
    -- Price data
    f.price_per_kg,
    f.price_bucket,
    
    -- Product details
    f.has_chicken,
    f.has_poultry,
    f.quality_score,
    
    -- URLs
    f.product_url,
    f.image_url,
    
    -- Source info
    f.source,
    
    -- Cast arrays to jsonb under original names (they're already arrays)
    f.ingredients_tokens::jsonb AS ingredients_tokens,
    f.available_countries::jsonb AS available_countries,
    f.sources::jsonb AS sources,
    
    -- Include allowlist status
    a.status AS allowlist_status,
    
    -- Timestamp
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
CREATE INDEX IF NOT EXISTS idx_foods_canonical_primary_protein ON foods_canonical (primary_protein) 
    WHERE primary_protein IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_foods_canonical_quality_score ON foods_canonical (quality_score);

-- Grant permissions (uncomment and adjust roles as needed)
-- GRANT SELECT ON foods_published_prod TO anon;
-- GRANT SELECT ON foods_published_prod TO authenticated;
-- GRANT SELECT ON foods_published_prod TO service_role;
-- GRANT SELECT ON foods_published_preview TO anon;
-- GRANT SELECT ON foods_published_preview TO authenticated;
-- GRANT SELECT ON foods_published_preview TO service_role;