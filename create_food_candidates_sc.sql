-- Create food_candidates_sc table for European retailer product data
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS food_candidates_sc (
    -- Primary key
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Basic product information
    brand text NOT NULL,
    product_name text NOT NULL,
    form text, -- dry, wet, raw, etc.
    life_stage text, -- puppy, adult, senior
    
    -- Nutrition information (per 100g)
    kcal_per_100g real,
    protein_percent real,
    fat_percent real,
    fiber_percent real,
    ash_percent real,
    moisture_percent real,
    carbs_percent real,
    
    -- Ingredients
    ingredients_raw text,
    ingredients_tokens text[],
    contains_chicken boolean DEFAULT false,
    grain_free boolean,
    
    -- Package information
    pack_sizes jsonb DEFAULT '[]'::jsonb,
    gtin text, -- barcode
    
    -- Retailer-specific columns
    retailer_source text, -- zooplus, fressnapf, maxizoo, etc.
    retailer_url text,
    retailer_product_id text,
    retailer_sku text,
    retailer_price_eur real,
    retailer_original_price_eur real,
    retailer_currency text DEFAULT 'EUR',
    retailer_in_stock boolean,
    retailer_stock_level integer,
    retailer_rating real, -- 1-5 scale
    retailer_review_count integer,
    
    -- Images
    image_url text, -- primary image
    image_urls text[], -- all product images
    image_primary_url text,
    
    -- Additional nutrition and feeding
    feeding_guidelines text,
    additives text,
    analytical_constituents_raw text,
    
    -- Geographic availability
    available_countries text[] DEFAULT ARRAY['UK'],
    shipping_countries text[],
    vat_included boolean DEFAULT true,
    
    -- API/Scraping metadata
    api_response jsonb,
    last_api_sync timestamptz,
    data_source text, -- 'api', 'scraper', 'manual'
    
    -- Timestamps
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    last_scraped_at timestamptz,
    
    -- Data quality
    fingerprint text, -- for deduplication
    data_complete boolean DEFAULT false,
    verified boolean DEFAULT false
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_brand 
    ON food_candidates_sc(brand);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_product_name 
    ON food_candidates_sc(product_name);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_retailer_source 
    ON food_candidates_sc(retailer_source);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_retailer_product_id 
    ON food_candidates_sc(retailer_product_id);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_brand_retailer 
    ON food_candidates_sc(brand, retailer_source);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_last_api_sync 
    ON food_candidates_sc(last_api_sync);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_data_source 
    ON food_candidates_sc(data_source);

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_grain_free 
    ON food_candidates_sc(grain_free) WHERE grain_free IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_food_candidates_sc_life_stage 
    ON food_candidates_sc(life_stage) WHERE life_stage IS NOT NULL;

-- Create unique constraint to prevent duplicates from same retailer
ALTER TABLE food_candidates_sc 
ADD CONSTRAINT unique_retailer_product_sc 
UNIQUE (brand, product_name, retailer_source, pack_sizes);

-- Create views for analysis

-- View for products with complete nutrition data
CREATE OR REPLACE VIEW food_candidates_sc_complete AS
SELECT * FROM food_candidates_sc
WHERE 
    protein_percent IS NOT NULL 
    AND fat_percent IS NOT NULL 
    AND brand IS NOT NULL 
    AND product_name IS NOT NULL
    AND ingredients_raw IS NOT NULL;

-- View for products by retailer
CREATE OR REPLACE VIEW food_candidates_sc_by_retailer AS
SELECT 
    retailer_source,
    COUNT(*) as product_count,
    COUNT(DISTINCT brand) as brand_count,
    AVG(retailer_price_eur) as avg_price,
    COUNT(CASE WHEN retailer_in_stock THEN 1 END) as in_stock_count,
    MAX(last_api_sync) as last_sync
FROM food_candidates_sc
WHERE retailer_source IS NOT NULL
GROUP BY retailer_source;

-- View for brand coverage
CREATE OR REPLACE VIEW food_candidates_sc_brand_coverage AS
SELECT 
    brand,
    COUNT(DISTINCT product_name) as product_count,
    COUNT(DISTINCT retailer_source) as retailer_count,
    AVG(retailer_price_eur) as avg_price,
    MIN(retailer_price_eur) as min_price,
    MAX(retailer_price_eur) as max_price,
    BOOL_OR(grain_free) as has_grain_free,
    ARRAY_AGG(DISTINCT life_stage) FILTER (WHERE life_stage IS NOT NULL) as life_stages,
    ARRAY_AGG(DISTINCT retailer_source) as retailers
FROM food_candidates_sc
GROUP BY brand
ORDER BY product_count DESC;

-- Function to check for duplicate products
CREATE OR REPLACE FUNCTION check_duplicate_product_sc(
    p_brand text,
    p_product_name text,
    p_retailer text
) RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM food_candidates_sc
        WHERE 
            brand = p_brand 
            AND product_name = p_product_name
            AND retailer_source = p_retailer
    );
END;
$$ LANGUAGE plpgsql;

-- Function to calculate completeness score
CREATE OR REPLACE FUNCTION calculate_completeness_score(product_id uuid)
RETURNS integer AS $$
DECLARE
    score integer := 0;
    rec RECORD;
BEGIN
    SELECT * INTO rec FROM food_candidates_sc WHERE id = product_id;
    
    IF rec.brand IS NOT NULL THEN score := score + 10; END IF;
    IF rec.product_name IS NOT NULL THEN score := score + 10; END IF;
    IF rec.ingredients_raw IS NOT NULL THEN score := score + 15; END IF;
    IF rec.protein_percent IS NOT NULL THEN score := score + 10; END IF;
    IF rec.fat_percent IS NOT NULL THEN score := score + 10; END IF;
    IF rec.fiber_percent IS NOT NULL THEN score := score + 5; END IF;
    IF rec.moisture_percent IS NOT NULL THEN score := score + 5; END IF;
    IF rec.kcal_per_100g IS NOT NULL THEN score := score + 10; END IF;
    IF rec.image_url IS NOT NULL OR rec.image_primary_url IS NOT NULL THEN score := score + 10; END IF;
    IF rec.retailer_price_eur IS NOT NULL THEN score := score + 5; END IF;
    IF rec.pack_sizes IS NOT NULL AND rec.pack_sizes != '[]'::jsonb THEN score := score + 5; END IF;
    IF rec.feeding_guidelines IS NOT NULL THEN score := score + 5; END IF;
    
    RETURN score; -- Max 100
END;
$$ LANGUAGE plpgsql;

-- Trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_food_candidates_sc_updated_at 
    BEFORE UPDATE ON food_candidates_sc
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments to table
COMMENT ON TABLE food_candidates_sc IS 'Dog food products from European retailers with complete nutrition data';
COMMENT ON COLUMN food_candidates_sc.brand IS 'Brand name (e.g., Royal Canin, Hills, Acana)';
COMMENT ON COLUMN food_candidates_sc.product_name IS 'Full product name including variant';
COMMENT ON COLUMN food_candidates_sc.kcal_per_100g IS 'Metabolizable energy per 100g';
COMMENT ON COLUMN food_candidates_sc.protein_percent IS 'Crude protein percentage';
COMMENT ON COLUMN food_candidates_sc.fat_percent IS 'Crude fat percentage';
COMMENT ON COLUMN food_candidates_sc.fiber_percent IS 'Crude fiber percentage';
COMMENT ON COLUMN food_candidates_sc.ash_percent IS 'Crude ash percentage';
COMMENT ON COLUMN food_candidates_sc.moisture_percent IS 'Moisture content percentage';
COMMENT ON COLUMN food_candidates_sc.pack_sizes IS 'Available package sizes as JSON array';
COMMENT ON COLUMN food_candidates_sc.fingerprint IS 'Hash for duplicate detection';

-- Grant appropriate permissions (adjust as needed)
GRANT ALL ON food_candidates_sc TO authenticated;
GRANT SELECT ON food_candidates_sc TO anon;
GRANT ALL ON food_candidates_sc_complete TO authenticated;
GRANT ALL ON food_candidates_sc_by_retailer TO authenticated;
GRANT ALL ON food_candidates_sc_brand_coverage TO authenticated;