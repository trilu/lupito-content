-- Manufacturer Enrichment SQL Scripts (CORRECTED)
-- Based on actual Supabase schema

-- ============================================
-- 1. ANALYSIS QUERIES
-- ============================================

-- Check current coverage by brand
SELECT 
    brand_slug,
    COUNT(*) as product_count,
    ROUND(AVG(CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as form_pct,
    ROUND(AVG(CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as life_stage_pct,
    ROUND(AVG(CASE WHEN kcal_per_100g IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as kcal_pct,
    ROUND(AVG(CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as ingredients_pct,
    ROUND(AVG(CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as price_pct,
    ROUND(AVG(
        CASE WHEN form IS NOT NULL THEN 0.2 ELSE 0 END +
        CASE WHEN life_stage IS NOT NULL THEN 0.2 ELSE 0 END +
        CASE WHEN kcal_per_100g IS NOT NULL THEN 0.2 ELSE 0 END +
        CASE WHEN ingredients_tokens IS NOT NULL THEN 0.2 ELSE 0 END +
        CASE WHEN price_per_kg IS NOT NULL THEN 0.2 ELSE 0 END
    ) * 100, 1) as overall_completion_pct
FROM foods_canonical
GROUP BY brand_slug
ORDER BY product_count DESC, overall_completion_pct ASC
LIMIT 50;

-- ============================================
-- 2. CREATE STAGING TABLE FOR HARVESTED DATA
-- ============================================

-- Create staging table for manufacturer harvest data
CREATE TABLE IF NOT EXISTS manufacturer_harvest_staging (
    id SERIAL PRIMARY KEY,
    brand_slug VARCHAR(255),
    product_name TEXT,
    product_url TEXT,
    form VARCHAR(50),
    life_stage VARCHAR(50),
    pack_size_kg DECIMAL(10,3),
    price DECIMAL(10,2),
    currency VARCHAR(10),
    price_per_kg DECIMAL(10,2),
    ingredients_raw TEXT,
    ingredients_tokens TEXT[],
    protein_percent DECIMAL(5,2),
    fat_percent DECIMAL(5,2),
    fibre_percent DECIMAL(5,2),
    moisture_percent DECIMAL(5,2),
    ash_percent DECIMAL(5,2),
    kcal_per_100g INTEGER,
    harvest_timestamp TIMESTAMP DEFAULT NOW(),
    harvest_batch VARCHAR(50),
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for matching
CREATE INDEX idx_harvest_brand_product ON manufacturer_harvest_staging(brand_slug, product_name);
CREATE INDEX idx_harvest_batch ON manufacturer_harvest_staging(harvest_batch);

-- ============================================
-- 3. MATCHING AND ENRICHMENT
-- ============================================

-- Create function to normalize product names for matching
CREATE OR REPLACE FUNCTION normalize_product_name(name TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(name, '[^a-zA-Z0-9\s]', '', 'g'),  -- Remove special chars
                '\s+', ' ', 'g'  -- Normalize spaces
            ),
            '^\s+|\s+$', '', 'g'  -- Trim
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Match harvested products with canonical products
CREATE OR REPLACE VIEW manufacturer_matches AS
SELECT 
    c.product_key,
    c.brand_slug,
    c.product_name as canonical_name,
    h.product_name as harvested_name,
    h.form as harvested_form,
    h.life_stage as harvested_life_stage,
    h.kcal_per_100g as harvested_kcal,
    h.ingredients_tokens as harvested_ingredients,
    h.price_per_kg as harvested_price,
    h.protein_percent as harvested_protein,
    h.fat_percent as harvested_fat,
    -- Calculate match confidence
    CASE 
        WHEN normalize_product_name(c.product_name) = normalize_product_name(h.product_name) THEN 1.0
        WHEN normalize_product_name(c.product_name) LIKE '%' || normalize_product_name(h.product_name) || '%' THEN 0.8
        WHEN normalize_product_name(h.product_name) LIKE '%' || normalize_product_name(c.product_name) || '%' THEN 0.8
        ELSE 0.5
    END as match_confidence
FROM foods_canonical c
INNER JOIN manufacturer_harvest_staging h 
    ON c.brand_slug = h.brand_slug
    AND (
        normalize_product_name(c.product_name) = normalize_product_name(h.product_name)
        OR normalize_product_name(c.product_name) LIKE '%' || normalize_product_name(h.product_name) || '%'
        OR normalize_product_name(h.product_name) LIKE '%' || normalize_product_name(c.product_name) || '%'
    );

-- ============================================
-- 4. UPDATE PREVIEW TABLE WITH ENRICHED DATA
-- ============================================

-- Update foods_published_preview with high-confidence matches
UPDATE foods_published_preview p
SET 
    form = COALESCE(p.form, m.harvested_form),
    life_stage = COALESCE(p.life_stage, m.harvested_life_stage),
    kcal_per_100g = COALESCE(p.kcal_per_100g, m.harvested_kcal),
    ingredients_tokens = CASE 
        WHEN p.ingredients_tokens IS NULL OR array_length(p.ingredients_tokens, 1) IS NULL 
        THEN m.harvested_ingredients 
        ELSE p.ingredients_tokens 
    END,
    price_per_kg = COALESCE(p.price_per_kg, m.harvested_price),
    protein_percent = COALESCE(p.protein_percent, m.harvested_protein),
    fat_percent = COALESCE(p.fat_percent, m.harvested_fat),
    sources = CASE 
        WHEN p.sources IS NULL THEN
            jsonb_build_object(
                'manufacturer_harvest', jsonb_build_object(
                    'timestamp', NOW(),
                    'confidence', m.match_confidence
                )
            )
        ELSE
            p.sources || jsonb_build_object(
                'manufacturer_harvest', jsonb_build_object(
                    'timestamp', NOW(),
                    'confidence', m.match_confidence
                )
            )
    END,
    updated_at = NOW()
FROM manufacturer_matches m
WHERE p.product_key = m.product_key
    AND m.match_confidence >= 0.9  -- Only high confidence matches
    AND (
        p.form IS NULL OR 
        p.life_stage IS NULL OR 
        p.kcal_per_100g IS NULL OR 
        p.ingredients_tokens IS NULL OR
        array_length(p.ingredients_tokens, 1) IS NULL OR
        p.price_per_kg IS NULL
    );  -- Only update missing fields

-- ============================================
-- 5. QUALITY VALIDATION
-- ============================================

-- Check for outliers in enriched data
SELECT 
    brand_slug,
    product_name,
    kcal_per_100g,
    price_per_kg,
    CASE 
        WHEN kcal_per_100g < 200 OR kcal_per_100g > 600 THEN 'KCAL_OUTLIER'
        WHEN price_per_kg < 0.5 OR price_per_kg > 50 THEN 'PRICE_OUTLIER'
        ELSE 'OK'
    END as validation_status
FROM foods_published_preview
WHERE brand_slug IN (
    SELECT DISTINCT brand_slug 
    FROM manufacturer_harvest_staging
)
AND (
    kcal_per_100g < 200 OR kcal_per_100g > 600 OR
    price_per_kg < 0.5 OR price_per_kg > 50
);

-- ============================================
-- 6. QUALITY GATES CHECK
-- ============================================

-- Check which brands meet quality gates after enrichment
WITH brand_quality AS (
    SELECT 
        brand_slug,
        COUNT(*) as total_products,
        -- Form gate (≥95%)
        ROUND(AVG(CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as form_pct,
        -- Life stage gate (≥95%)
        ROUND(AVG(CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as life_stage_pct,
        -- Valid kcal gate (≥90% in 200-600 range)
        ROUND(AVG(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 ELSE 0 END) * 100, 1) as valid_kcal_pct,
        -- Ingredients gate (≥85%)
        ROUND(AVG(CASE WHEN ingredients_tokens IS NOT NULL AND array_length(ingredients_tokens, 1) > 0 THEN 1 ELSE 0 END) * 100, 1) as ingredients_pct,
        -- Price gate (≥70%)
        ROUND(AVG(CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 0 END) * 100, 1) as price_pct
    FROM foods_published_preview
    WHERE brand_slug IN (
        SELECT DISTINCT brand_slug 
        FROM manufacturer_harvest_staging
    )
    GROUP BY brand_slug
)
SELECT 
    brand_slug,
    total_products,
    form_pct,
    life_stage_pct,
    valid_kcal_pct,
    ingredients_pct,
    price_pct,
    CASE 
        WHEN form_pct >= 95 
            AND life_stage_pct >= 95 
            AND valid_kcal_pct >= 90 
            AND ingredients_pct >= 85 
            AND price_pct >= 70 
        THEN '✅ PASS ALL GATES'
        ELSE '❌ FAILS GATES'
    END as gate_status
FROM brand_quality
ORDER BY 
    CASE 
        WHEN form_pct >= 95 
            AND life_stage_pct >= 95 
            AND valid_kcal_pct >= 90 
            AND ingredients_pct >= 85 
            AND price_pct >= 70 
        THEN 0 
        ELSE 1 
    END,
    total_products DESC;

-- ============================================
-- 7. PROMOTION TO PRODUCTION
-- ============================================

-- Generate SQL to promote qualifying brands to production
WITH qualifying_brands AS (
    SELECT brand_slug
    FROM foods_published_preview
    WHERE brand_slug IN (
        SELECT DISTINCT brand_slug 
        FROM manufacturer_harvest_staging
    )
    GROUP BY brand_slug
    HAVING 
        AVG(CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) >= 0.95
        AND AVG(CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END) >= 0.95
        AND AVG(CASE WHEN kcal_per_100g BETWEEN 200 AND 600 THEN 1 ELSE 0 END) >= 0.90
        AND AVG(CASE WHEN ingredients_tokens IS NOT NULL AND array_length(ingredients_tokens, 1) > 0 THEN 1 ELSE 0 END) >= 0.85
        AND AVG(CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 0 END) >= 0.70
)
SELECT 
    '-- Promote brand: ' || brand_slug || E'\n' ||
    'UPDATE foods_published_prod SET ' || E'\n' ||
    '  form = preview.form,' || E'\n' ||
    '  life_stage = preview.life_stage,' || E'\n' ||
    '  kcal_per_100g = preview.kcal_per_100g,' || E'\n' ||
    '  ingredients_tokens = preview.ingredients_tokens,' || E'\n' ||
    '  price_per_kg = preview.price_per_kg,' || E'\n' ||
    '  protein_percent = preview.protein_percent,' || E'\n' ||
    '  fat_percent = preview.fat_percent,' || E'\n' ||
    '  sources = preview.sources,' || E'\n' ||
    '  updated_at = NOW()' || E'\n' ||
    'FROM foods_published_preview preview' || E'\n' ||
    'WHERE foods_published_prod.product_key = preview.product_key' || E'\n' ||
    '  AND preview.brand_slug = ''' || brand_slug || ''';' as promotion_sql
FROM qualifying_brands;

-- ============================================
-- 8. REPORTING QUERIES
-- ============================================

-- Delta report: before and after enrichment
WITH before_stats AS (
    SELECT 
        brand_slug,
        COUNT(*) as total,
        AVG(CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) * 100 as form_before,
        AVG(CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END) * 100 as life_before,
        AVG(CASE WHEN kcal_per_100g IS NOT NULL THEN 1 ELSE 0 END) * 100 as kcal_before,
        AVG(CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END) * 100 as ingredients_before,
        AVG(CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 0 END) * 100 as price_before
    FROM foods_canonical
    WHERE brand_slug IN (SELECT DISTINCT brand_slug FROM manufacturer_harvest_staging)
    GROUP BY brand_slug
),
after_stats AS (
    SELECT 
        brand_slug,
        AVG(CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) * 100 as form_after,
        AVG(CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END) * 100 as life_after,
        AVG(CASE WHEN kcal_per_100g IS NOT NULL THEN 1 ELSE 0 END) * 100 as kcal_after,
        AVG(CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END) * 100 as ingredients_after,
        AVG(CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 0 END) * 100 as price_after
    FROM foods_published_preview
    WHERE brand_slug IN (SELECT DISTINCT brand_slug FROM manufacturer_harvest_staging)
    GROUP BY brand_slug
)
SELECT 
    b.brand_slug,
    b.total as products,
    ROUND(b.form_before, 1) || '% → ' || ROUND(a.form_after, 1) || '%' as form_delta,
    ROUND(b.life_before, 1) || '% → ' || ROUND(a.life_after, 1) || '%' as life_stage_delta,
    ROUND(b.kcal_before, 1) || '% → ' || ROUND(a.kcal_after, 1) || '%' as kcal_delta,
    ROUND(b.ingredients_before, 1) || '% → ' || ROUND(a.ingredients_after, 1) || '%' as ingredients_delta,
    ROUND(b.price_before, 1) || '% → ' || ROUND(a.price_after, 1) || '%' as price_delta
FROM before_stats b
JOIN after_stats a ON b.brand_slug = a.brand_slug
ORDER BY b.total DESC;

-- ============================================
-- 9. SAMPLE DATA CHECK
-- ============================================

-- View sample of enriched products
SELECT 
    p.brand_slug,
    p.product_name,
    p.form,
    p.life_stage,
    p.kcal_per_100g,
    p.price_per_kg,
    p.ingredients_tokens[1:5] as first_5_ingredients,
    p.sources->>'manufacturer_harvest' as harvest_info
FROM foods_published_preview p
WHERE p.brand_slug IN (
    SELECT DISTINCT brand_slug 
    FROM manufacturer_harvest_staging
)
AND p.sources ? 'manufacturer_harvest'
LIMIT 20;