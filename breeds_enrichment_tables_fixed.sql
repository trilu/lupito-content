-- ============================================
-- BREEDS ENRICHMENT TABLES - FIXED VERSION
-- ============================================

-- 1. Create breeds_enrichment table (if it doesn't exist)
CREATE TABLE IF NOT EXISTS breeds_enrichment (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    field_numeric NUMERIC,
    source TEXT NOT NULL, -- 'wikipedia', 'akc', 'fci', 'manual'
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    confidence_score NUMERIC DEFAULT 1.0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(breed_slug, field_name, source)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_breeds_enrichment_slug ON breeds_enrichment(breed_slug);
CREATE INDEX IF NOT EXISTS idx_breeds_enrichment_field ON breeds_enrichment(field_name);
CREATE INDEX IF NOT EXISTS idx_breeds_enrichment_source ON breeds_enrichment(source);

-- 2. breeds_overrides table already exists with different structure
-- Let's just add any missing columns if needed
-- The existing table stores direct value overrides for each field

-- 3. Create breeds_wikipedia_cache table for storing Wikipedia data
CREATE TABLE IF NOT EXISTS breeds_wikipedia_cache (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL UNIQUE,
    wikipedia_url TEXT,
    html_content TEXT,
    extracted_data JSONB,
    gcs_html_path TEXT,
    gcs_json_path TEXT,
    scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_breeds_wikipedia_cache_slug ON breeds_wikipedia_cache(breed_slug);

-- 4. Create a tracking table for enrichment runs
CREATE TABLE IF NOT EXISTS breeds_enrichment_runs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    breeds_processed INTEGER DEFAULT 0,
    breeds_enriched INTEGER DEFAULT 0,
    breeds_failed INTEGER DEFAULT 0,
    gcs_folder TEXT,
    notes TEXT
);

-- Grant permissions
GRANT ALL ON breeds_enrichment TO authenticated;
GRANT ALL ON breeds_wikipedia_cache TO authenticated;
GRANT ALL ON breeds_enrichment_runs TO authenticated;

-- Grant sequence permissions
GRANT USAGE, SELECT ON SEQUENCE breeds_enrichment_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE breeds_wikipedia_cache_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE breeds_enrichment_runs_id_seq TO authenticated;