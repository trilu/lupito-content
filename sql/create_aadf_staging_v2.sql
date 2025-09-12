
-- Drop and recreate staging table v2
DROP TABLE IF EXISTS retailer_staging_aadf_v2 CASCADE;

CREATE TABLE retailer_staging_aadf_v2 (
    brand_raw TEXT,
    brand_slug VARCHAR(255),
    product_name_raw TEXT,
    product_name_norm VARCHAR(255),
    url TEXT,
    image_url TEXT,
    form_guess VARCHAR(50),
    life_stage_guess VARCHAR(50),
    ingredients_raw TEXT,
    ingredients_language VARCHAR(10),
    kcal_per_100g DECIMAL(6,2),
    protein_percent DECIMAL(5,2),
    fat_percent DECIMAL(5,2),
    fiber_percent DECIMAL(5,2),
    ash_percent DECIMAL(5,2),
    moisture_percent DECIMAL(5,2),
    pack_sizes TEXT,
    gtin VARCHAR(20),
    source VARCHAR(20) DEFAULT 'aadf',
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    row_hash VARCHAR(64),
    product_key_candidate VARCHAR(32) PRIMARY KEY
);

-- Create indexes
CREATE INDEX idx_aadf_v2_brand_slug ON retailer_staging_aadf_v2(brand_slug);
CREATE INDEX idx_aadf_v2_form ON retailer_staging_aadf_v2(form_guess);
CREATE INDEX idx_aadf_v2_life_stage ON retailer_staging_aadf_v2(life_stage_guess);
CREATE INDEX idx_aadf_v2_row_hash ON retailer_staging_aadf_v2(row_hash);
