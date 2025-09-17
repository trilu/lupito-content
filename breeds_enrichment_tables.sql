-- ============================================
-- BREEDS ENRICHMENT TABLES CREATION
-- ============================================

-- 1. Create breeds_enrichment table for storing enriched data from multiple sources
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

-- 2. Create breeds_overrides table for manual corrections
CREATE TABLE IF NOT EXISTS breeds_overrides (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL,
    field_name TEXT NOT NULL,
    original_value TEXT,
    override_value TEXT,
    override_reason TEXT NOT NULL,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(breed_slug, field_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_breeds_overrides_slug ON breeds_overrides(breed_slug);
CREATE INDEX IF NOT EXISTS idx_breeds_overrides_applied ON breeds_overrides(applied);

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

-- Grant permissions
GRANT ALL ON breeds_enrichment TO authenticated;
GRANT ALL ON breeds_overrides TO authenticated;
GRANT ALL ON breeds_wikipedia_cache TO authenticated;

-- Grant sequence permissions
GRANT USAGE, SELECT ON SEQUENCE breeds_enrichment_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE breeds_overrides_id_seq TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE breeds_wikipedia_cache_id_seq TO authenticated;