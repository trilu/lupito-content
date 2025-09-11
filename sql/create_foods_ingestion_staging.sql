-- Create staging table for safe ingredient ingestion
-- B1A: Server-side merge workflow

CREATE TABLE IF NOT EXISTS foods_ingestion_staging (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    brand TEXT NOT NULL,
    brand_slug TEXT NOT NULL,
    product_name_raw TEXT NOT NULL,
    name_slug TEXT NOT NULL,
    product_key_computed TEXT NOT NULL,
    product_url TEXT,
    ingredients_raw TEXT,
    ingredients_tokens TEXT[],
    ingredients_language TEXT,
    ingredients_source TEXT,
    ingredients_parsed_at TIMESTAMP WITH TIME ZONE,
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    debug_blob JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for efficient joins during merge
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_run_id ON foods_ingestion_staging(run_id);
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_product_key ON foods_ingestion_staging(product_key_computed);
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_brand_name ON foods_ingestion_staging(brand_slug, name_slug);

-- Comments for documentation
COMMENT ON TABLE foods_ingestion_staging IS 'Staging table for ingredient extractions before server-side merge into foods_canonical';
COMMENT ON COLUMN foods_ingestion_staging.run_id IS 'Unique identifier for each extraction batch run';
COMMENT ON COLUMN foods_ingestion_staging.product_key_computed IS 'MD5 hash used for matching with foods_canonical.product_key';
COMMENT ON COLUMN foods_ingestion_staging.debug_blob IS 'JSON debug information from extraction process';