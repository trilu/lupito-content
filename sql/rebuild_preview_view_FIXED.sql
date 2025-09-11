-- Rebuild foods_published_preview with correct column names
DROP VIEW IF EXISTS foods_published_preview CASCADE;

CREATE OR REPLACE VIEW foods_published_preview AS
SELECT 
    -- Core fields
    f.brand,
    f.product_name,
    f.brand_slug,
    f.name_slug,
    f.product_key,
    f.product_url,
    f.image_url,
    f.source,
    
    -- Form and life stage (may be null)
    f.form,
    f.life_stage,
    
    -- Arrays as JSONB
    f.ingredients_tokens::jsonb AS ingredients_tokens,
    f.available_countries::jsonb AS available_countries,
    f.sources::jsonb AS sources,
    
    -- Nutrition
    f.kcal_per_100g,
    f.kcal_per_100g_final,
    f.kcal_is_estimated,
    f.protein_percent,
    f.fat_percent,
    f.primary_protein,
    
    -- Pricing (may be null)
    f.price_per_kg,
    f.price_bucket,
    
    -- Quality and allergens
    f.quality_score,
    f.has_chicken,
    f.has_poultry,
    
    -- Metadata
    f.updated_at,
    
    -- Allowlist status
    COALESCE(ba.status, 'PENDING') AS allowlist_status,
    ba.updated_at AS allowlist_updated_at
FROM 
    foods_canonical f
LEFT JOIN 
    brand_allowlist ba ON f.brand_slug = ba.brand_slug
WHERE 
    -- Include ACTIVE and PENDING for preview
    (ba.status IN ('ACTIVE', 'PENDING') OR ba.status IS NULL);

-- Grant permissions
GRANT SELECT ON foods_published_preview TO authenticated;
GRANT SELECT ON foods_published_preview TO anon;