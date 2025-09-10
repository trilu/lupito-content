-- Grade A+ Schema Additions for Breeds Database
-- Execute in Supabase SQL Editor

-- 1. Create breeds_overrides table
CREATE TABLE IF NOT EXISTS breeds_overrides (
    id SERIAL PRIMARY KEY,
    breed_slug VARCHAR(255) UNIQUE NOT NULL,
    size_category VARCHAR(10) CHECK (size_category IN ('xs', 's', 'm', 'l', 'xl')),
    growth_end_months INTEGER,
    senior_start_months INTEGER,
    adult_weight_min_kg DECIMAL(5,2),
    adult_weight_max_kg DECIMAL(5,2),
    adult_weight_avg_kg DECIMAL(5,2),
    height_min_cm DECIMAL(5,2),
    height_max_cm DECIMAL(5,2),
    lifespan_min_years DECIMAL(4,1),
    lifespan_max_years DECIMAL(4,1),
    lifespan_avg_years DECIMAL(4,1),
    override_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create breeds_enrichment table
CREATE TABLE IF NOT EXISTS breeds_enrichment (
    id SERIAL PRIMARY KEY,
    breed_slug VARCHAR(255) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_value TEXT,
    source VARCHAR(50) NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
    extraction_method VARCHAR(100),
    confidence DECIMAL(3,2),
    raw_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(breed_slug, field_name, source)
);

-- 3. Add columns to breeds_details
ALTER TABLE breeds_details 
ADD COLUMN IF NOT EXISTS size_category VARCHAR(10) CHECK (size_category IN ('xs', 's', 'm', 'l', 'xl')),
ADD COLUMN IF NOT EXISTS growth_end_months INTEGER,
ADD COLUMN IF NOT EXISTS senior_start_months INTEGER,
ADD COLUMN IF NOT EXISTS adult_weight_avg_kg DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS lifespan_avg_years DECIMAL(4,1),
ADD COLUMN IF NOT EXISTS size_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS age_bounds_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS weight_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS height_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS lifespan_from VARCHAR(20),
ADD COLUMN IF NOT EXISTS conflict_flags TEXT[];

-- 4. Create indexes
CREATE INDEX IF NOT EXISTS idx_breeds_overrides_slug ON breeds_overrides(breed_slug);
CREATE INDEX IF NOT EXISTS idx_breeds_enrichment_slug ON breeds_enrichment(breed_slug);
CREATE INDEX IF NOT EXISTS idx_breeds_enrichment_field ON breeds_enrichment(breed_slug, field_name);

-- 5. Initial overrides
INSERT INTO breeds_overrides (breed_slug, size_category, adult_weight_min_kg, adult_weight_max_kg, adult_weight_avg_kg, override_reason)
VALUES 
    ('labrador-retriever', 'l', 25.0, 36.0, 30.0, 'Correcting to large size category'),
    ('japanese-chin', 's', 1.8, 4.1, 3.0, 'Fixed 537kg error'),
    ('great-dane', 'xl', 54.0, 90.0, 72.0, 'Fixed 27kg error')
ON CONFLICT (breed_slug) DO UPDATE
SET 
    size_category = EXCLUDED.size_category,
    adult_weight_min_kg = EXCLUDED.adult_weight_min_kg,
    adult_weight_max_kg = EXCLUDED.adult_weight_max_kg,
    adult_weight_avg_kg = EXCLUDED.adult_weight_avg_kg,
    override_reason = EXCLUDED.override_reason,
    updated_at = NOW();
