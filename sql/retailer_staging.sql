-- ============================================================================
-- RETAILER STAGING TABLES DDL
-- ============================================================================
-- Purpose: Create staging tables for retailer data review (Chewy + AADF)
-- Generated: 2025-09-12
-- Status: FOR REVIEW ONLY - DO NOT AUTO-EXECUTE
-- ============================================================================

-- Drop existing staging tables if needed (careful!)
-- DROP TABLE IF EXISTS retailer_staging_chewy CASCADE;
-- DROP TABLE IF EXISTS retailer_staging_aadf CASCADE;
-- DROP TABLE IF EXISTS retailer_staging_combined CASCADE;

-- ============================================================================
-- CHEWY STAGING TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS retailer_staging_chewy (
    -- Primary identification
    product_key VARCHAR(255) PRIMARY KEY,
    brand VARCHAR(255),
    brand_slug VARCHAR(255),
    brand_family VARCHAR(255),
    product_name TEXT,
    name_slug VARCHAR(255),
    
    -- Product attributes
    form VARCHAR(50),
    life_stage VARCHAR(50),
    
    -- Nutrition (not available from Chewy)
    kcal_per_100g DECIMAL(6,2),
    protein_percent DECIMAL(5,2),
    fat_percent DECIMAL(5,2),
    fiber_percent DECIMAL(5,2),
    ash_percent DECIMAL(5,2),
    moisture_percent DECIMAL(5,2),
    
    -- Ingredients (not available from Chewy)
    ingredients_raw TEXT,
    ingredients_tokens JSONB,
    
    -- Pricing
    price_per_kg_eur DECIMAL(10,2),
    price_bucket VARCHAR(20),
    
    -- Metadata
    available_countries JSONB DEFAULT '["US"]'::jsonb,
    sources JSONB,
    product_url TEXT,
    staging_source VARCHAR(20) DEFAULT 'chewy',
    staging_confidence DECIMAL(3,2),
    
    -- Timestamps
    staged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    review_notes TEXT
);

-- Indexes for Chewy staging
CREATE INDEX idx_chewy_brand_slug ON retailer_staging_chewy(brand_slug);
CREATE INDEX idx_chewy_form ON retailer_staging_chewy(form);
CREATE INDEX idx_chewy_life_stage ON retailer_staging_chewy(life_stage);
CREATE INDEX idx_chewy_confidence ON retailer_staging_chewy(staging_confidence);
CREATE INDEX idx_chewy_review_status ON retailer_staging_chewy(review_status);

-- ============================================================================
-- AADF STAGING TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS retailer_staging_aadf (
    -- Primary identification
    product_key VARCHAR(255) PRIMARY KEY,
    brand VARCHAR(255),
    brand_slug VARCHAR(255),
    brand_family VARCHAR(255),
    product_name TEXT,
    name_slug VARCHAR(255),
    
    -- Product attributes
    form VARCHAR(50),
    life_stage VARCHAR(50),
    
    -- Nutrition (limited in AADF)
    kcal_per_100g DECIMAL(6,2),
    protein_percent DECIMAL(5,2),
    fat_percent DECIMAL(5,2),
    fiber_percent DECIMAL(5,2),
    ash_percent DECIMAL(5,2),
    moisture_percent DECIMAL(5,2),
    
    -- Ingredients (available in AADF)
    ingredients_raw TEXT,
    ingredients_tokens JSONB,
    
    -- Pricing
    price_per_kg_eur DECIMAL(10,2),
    price_bucket VARCHAR(20),
    
    -- Metadata
    available_countries JSONB DEFAULT '["UK"]'::jsonb,
    sources JSONB,
    product_url TEXT,
    staging_source VARCHAR(20) DEFAULT 'aadf',
    staging_confidence DECIMAL(3,2),
    
    -- Timestamps
    staged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_status VARCHAR(20) DEFAULT 'pending',
    review_notes TEXT
);

-- Indexes for AADF staging
CREATE INDEX idx_aadf_brand_slug ON retailer_staging_aadf(brand_slug);
CREATE INDEX idx_aadf_form ON retailer_staging_aadf(form);
CREATE INDEX idx_aadf_life_stage ON retailer_staging_aadf(life_stage);
CREATE INDEX idx_aadf_confidence ON retailer_staging_aadf(staging_confidence);
CREATE INDEX idx_aadf_review_status ON retailer_staging_aadf(review_status);

-- ============================================================================
-- COMBINED VIEW FOR ANALYSIS
-- ============================================================================
CREATE OR REPLACE VIEW retailer_staging_combined AS
SELECT 
    product_key,
    brand,
    brand_slug,
    brand_family,
    product_name,
    name_slug,
    form,
    life_stage,
    kcal_per_100g,
    protein_percent,
    fat_percent,
    fiber_percent,
    ash_percent,
    moisture_percent,
    ingredients_raw,
    ingredients_tokens,
    price_per_kg_eur,
    price_bucket,
    available_countries,
    sources,
    product_url,
    staging_source,
    staging_confidence,
    staged_at,
    review_status
FROM retailer_staging_chewy

UNION ALL

SELECT 
    product_key,
    brand,
    brand_slug,
    brand_family,
    product_name,
    name_slug,
    form,
    life_stage,
    kcal_per_100g,
    protein_percent,
    fat_percent,
    fiber_percent,
    ash_percent,
    moisture_percent,
    ingredients_raw,
    ingredients_tokens,
    price_per_kg_eur,
    price_bucket,
    available_countries,
    sources,
    product_url,
    staging_source,
    staging_confidence,
    staged_at,
    review_status
FROM retailer_staging_aadf;

-- ============================================================================
-- ANALYSIS QUERIES
-- ============================================================================

-- Coverage summary by source
CREATE OR REPLACE VIEW retailer_staging_coverage AS
SELECT 
    staging_source,
    COUNT(*) as total_products,
    COUNT(CASE WHEN form IS NOT NULL THEN 1 END) as has_form,
    COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) as has_life_stage,
    COUNT(CASE WHEN ingredients_raw IS NOT NULL THEN 1 END) as has_ingredients,
    COUNT(CASE WHEN price_per_kg_eur IS NOT NULL THEN 1 END) as has_price,
    COUNT(CASE WHEN staging_confidence >= 0.7 THEN 1 END) as high_confidence,
    ROUND(AVG(staging_confidence), 2) as avg_confidence
FROM retailer_staging_combined
GROUP BY staging_source;

-- Brand distribution
CREATE OR REPLACE VIEW retailer_staging_brands AS
SELECT 
    brand,
    brand_slug,
    COUNT(*) as product_count,
    COUNT(DISTINCT staging_source) as source_count,
    STRING_AGG(DISTINCT staging_source, ', ') as sources,
    ROUND(AVG(staging_confidence), 2) as avg_confidence,
    COUNT(CASE WHEN form IS NOT NULL THEN 1 END) as with_form,
    COUNT(CASE WHEN life_stage IS NOT NULL THEN 1 END) as with_life_stage
FROM retailer_staging_combined
GROUP BY brand, brand_slug
ORDER BY product_count DESC;

-- ============================================================================
-- MERGE PREPARATION QUERIES
-- ============================================================================

-- High confidence products ready for merge
CREATE OR REPLACE VIEW retailer_staging_merge_ready AS
SELECT *
FROM retailer_staging_combined
WHERE staging_confidence >= 0.7
  AND review_status = 'approved'
  AND form IS NOT NULL
  AND life_stage IS NOT NULL;

-- Potential duplicates across sources
CREATE OR REPLACE VIEW retailer_staging_duplicates AS
SELECT 
    r1.product_key as key1,
    r1.product_name as name1,
    r1.staging_source as source1,
    r2.product_key as key2,
    r2.product_name as name2,
    r2.staging_source as source2
FROM retailer_staging_combined r1
JOIN retailer_staging_combined r2 
  ON r1.brand_slug = r2.brand_slug
  AND r1.name_slug = r2.name_slug
  AND r1.staging_source < r2.staging_source;

-- ============================================================================
-- DATA LOADING (example - adjust paths)
-- ============================================================================
-- Load from CSV files using COPY command:
-- 
-- \COPY retailer_staging_chewy FROM '/path/to/retailer_staging.chewy.csv' 
--   WITH (FORMAT csv, HEADER true, NULL '');
-- 
-- \COPY retailer_staging_aadf FROM '/path/to/retailer_staging.aadf.csv' 
--   WITH (FORMAT csv, HEADER true, NULL '');

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. This is a STAGING schema - not for production use
-- 2. Review products before merging to foods_canonical
-- 3. Use staging_confidence field to filter quality
-- 4. Preserve retailer attribution in sources array
-- 5. Do not override manufacturer data with retailer data
-- ============================================================================