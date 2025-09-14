-- Create temporary table for products missing ingredients
-- This will hold the exact 227 products that need to be scraped

-- Drop table if it exists
DROP TABLE IF EXISTS zooplus_missing_ingredients;

-- Create the table
CREATE TABLE zooplus_missing_ingredients (
    id SERIAL PRIMARY KEY,
    product_key TEXT NOT NULL,
    product_name TEXT,
    brand TEXT,
    product_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    scraped_at TIMESTAMP NULL,
    processing_status TEXT DEFAULT 'pending' -- pending, scraped, processed, failed
);

-- Insert products that are missing ingredients
INSERT INTO zooplus_missing_ingredients (product_key, product_name, brand, product_url)
SELECT 
    product_key,
    product_name,
    brand,
    product_url
FROM foods_canonical 
WHERE product_url ILIKE '%zooplus%' 
    AND ingredients_raw IS NULL
ORDER BY product_key;

-- Create indexes for faster queries
CREATE INDEX idx_zooplus_missing_status ON zooplus_missing_ingredients(processing_status);
CREATE INDEX idx_zooplus_missing_scraped ON zooplus_missing_ingredients(scraped_at);
CREATE INDEX idx_zooplus_missing_product_key ON zooplus_missing_ingredients(product_key);

-- Show summary
SELECT 
    COUNT(*) as total_missing,
    COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
    COUNT(*) FILTER (WHERE processing_status = 'scraped') as scraped,
    COUNT(*) FILTER (WHERE processing_status = 'processed') as processed,
    COUNT(*) FILTER (WHERE processing_status = 'failed') as failed
FROM zooplus_missing_ingredients;

-- Show first 10 products as sample
SELECT 
    id,
    product_key,
    LEFT(product_name, 50) || '...' as product_name_preview,
    brand,
    processing_status
FROM zooplus_missing_ingredients 
ORDER BY id 
LIMIT 10;