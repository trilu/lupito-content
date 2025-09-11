-- Rebuild foods_published_preview with updated canonical data
DROP VIEW IF EXISTS foods_published_preview CASCADE;

CREATE OR REPLACE VIEW foods_published_preview AS
SELECT 
    f.id,
    f.brand,
    f.product_name,
    f.brand_slug,
    f.product_variant,
    f.description,
    f.form,
    f.life_stage,
    f.special_needs,
    f.breed_size,
    
    -- Ensure arrays are JSONB
    f.ingredients_tokens::jsonb AS ingredients_tokens,
    f.available_countries::jsonb AS available_countries,
    f.sources::jsonb AS sources,
    COALESCE(f.allergens::jsonb, '[]'::jsonb) AS allergens,
    
    -- Nutrition & Pricing
    f.kcal_per_100g,
    f.protein_percent,
    f.fat_percent,
    f.fiber_percent,
    f.moisture_percent,
    f.price,
    f.price_per_kg,
    f.price_bucket,
    f.pack_size_raw,
    
    -- Metadata
    f.created_at,
    f.updated_at,
    f.data_source,
    
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
