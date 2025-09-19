-- Zooplus Staging Table for Import Process
-- Purpose: Store and process Zooplus data before importing to main database

DROP TABLE IF EXISTS zooplus_staging CASCADE;

CREATE TABLE zooplus_staging (
    id SERIAL PRIMARY KEY,
    product_key TEXT NOT NULL,
    brand TEXT,
    product_name TEXT,
    product_url TEXT UNIQUE,
    base_url TEXT,  -- URL without variant parameters
    food_type TEXT CHECK (food_type IN ('wet', 'dry', 'unknown')),
    has_ingredients BOOLEAN DEFAULT FALSE,
    ingredients_preview TEXT,
    source_file TEXT,
    is_variant BOOLEAN DEFAULT FALSE,
    variant_of_url TEXT,  -- Reference to base product
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    matched_product_key TEXT,
    match_type TEXT CHECK (match_type IN ('exact_url', 'brand_name', 'fuzzy', 'new', NULL)),
    match_confidence DECIMAL(3,2)
);

-- Indexes for performance
CREATE INDEX idx_zooplus_staging_base_url ON zooplus_staging(base_url);
CREATE INDEX idx_zooplus_staging_brand ON zooplus_staging(brand);
CREATE INDEX idx_zooplus_staging_product_key ON zooplus_staging(product_key);
CREATE INDEX idx_zooplus_staging_processed ON zooplus_staging(processed);
CREATE INDEX idx_zooplus_staging_is_variant ON zooplus_staging(is_variant);
CREATE INDEX idx_zooplus_staging_match_type ON zooplus_staging(match_type);

-- Grant permissions
GRANT ALL ON zooplus_staging TO authenticated;
GRANT ALL ON zooplus_staging TO service_role;
GRANT ALL ON zooplus_staging_id_seq TO authenticated;
GRANT ALL ON zooplus_staging_id_seq TO service_role;

-- Add comment
COMMENT ON TABLE zooplus_staging IS 'Staging table for Zooplus product import - tracks variants and matching';
