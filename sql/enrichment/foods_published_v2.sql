-- Generated: 2025-09-10 15:32:53
-- Purpose: Foods Published V2

-- Foods Published V2 Reconciled View with All Enrichments
-- Generated: 2025-09-10 15:32:53

CREATE OR REPLACE VIEW foods_published_v2 AS
SELECT 
    fp.*,
    -- Enriched fields
    ea.allergen_groups,
    ec.form as form_enriched,
    ec.life_stage as life_stage_enriched,
    ep.price_per_kg_eur as price_per_kg_enriched,
    ep.price_bucket as price_bucket_enriched,
    ek.new_kcal as kcal_fixed,
    
    -- Reconciled fields with precedence
    COALESCE(fo.allergen_groups, ea.allergen_groups, fp.allergen_groups) as allergen_groups_final,
    COALESCE(fo.form, ec.form, fp.form) as form_final,
    COALESCE(fo.life_stage, ec.life_stage, fp.life_stage) as life_stage_final,
    COALESCE(fo.price_bucket, ep.price_bucket, fp.price_bucket) as price_bucket_final,
    COALESCE(ek.new_kcal, fp.kcal_per_100g) as kcal_per_100g_final,
    
    -- Provenance flags
    CASE 
        WHEN fo.form IS NOT NULL THEN 'override'
        WHEN ec.form IS NOT NULL AND ec.form != fp.form THEN 'enrichment'
        WHEN fp.form IS NOT NULL THEN 'source'
        ELSE 'default'
    END as form_from,
    
    CASE 
        WHEN fo.life_stage IS NOT NULL THEN 'override'
        WHEN ec.life_stage IS NOT NULL AND ec.life_stage != fp.life_stage THEN 'enrichment'
        WHEN fp.life_stage IS NOT NULL THEN 'source'
        ELSE 'default'
    END as life_stage_from,
    
    '2025-09-10 15:32:53' as enriched_at,
    'v2' as catalog_version
    
FROM foods_published fp
LEFT JOIN foods_enrichment_allergens ea ON fp.product_key = ea.product_key
LEFT JOIN foods_enrichment_classify_v2 ec ON fp.product_key = ec.product_key
LEFT JOIN foods_enrichment_prices_v2 ep ON fp.product_key = ep.product_key
LEFT JOIN foods_enrichment_kcal_fixes ek ON fp.product_key = ek.product_key
LEFT JOIN foods_overrides fo ON fp.product_key = fo.product_key;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_v2_product_key ON foods_published_v2(product_key);
CREATE INDEX IF NOT EXISTS idx_v2_brand ON foods_published_v2(brand_slug);
CREATE INDEX IF NOT EXISTS idx_v2_form ON foods_published_v2(form_final);
CREATE INDEX IF NOT EXISTS idx_v2_life_stage ON foods_published_v2(life_stage_final);
CREATE INDEX IF NOT EXISTS idx_v2_price_bucket ON foods_published_v2(price_bucket_final);
