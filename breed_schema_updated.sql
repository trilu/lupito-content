-- Updated Breed Schema for Dogo Scraper
-- Preserves existing breeds table, adds new tables for Dogo content
-- Execute this SQL in your Supabase dashboard

-- Create enum types for controlled vocabularies (if they don't exist)
DO $$ BEGIN
    CREATE TYPE dogo_size_enum AS ENUM ('tiny', 'small', 'medium', 'large', 'giant');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dogo_energy_enum AS ENUM ('low', 'moderate', 'high', 'very_high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dogo_coat_length_enum AS ENUM ('short', 'medium', 'long');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dogo_shedding_enum AS ENUM ('minimal', 'low', 'moderate', 'high', 'very_high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dogo_trainability_enum AS ENUM ('challenging', 'moderate', 'easy', 'very_easy');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE dogo_bark_level_enum AS ENUM ('quiet', 'occasional', 'moderate', 'frequent', 'very_vocal');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE text_status_enum AS ENUM ('draft', 'published');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add missing columns to existing breeds table (safely)
ALTER TABLE breeds 
ADD COLUMN IF NOT EXISTS breed_slug TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS aliases TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS dogo_size dogo_size_enum,
ADD COLUMN IF NOT EXISTS dogo_energy dogo_energy_enum,
ADD COLUMN IF NOT EXISTS dogo_coat_length dogo_coat_length_enum,
ADD COLUMN IF NOT EXISTS dogo_shedding dogo_shedding_enum,
ADD COLUMN IF NOT EXISTS dogo_trainability dogo_trainability_enum,
ADD COLUMN IF NOT EXISTS dogo_bark_level dogo_bark_level_enum,
ADD COLUMN IF NOT EXISTS dogo_lifespan_years_min INTEGER,
ADD COLUMN IF NOT EXISTS dogo_lifespan_years_max INTEGER,
ADD COLUMN IF NOT EXISTS dogo_weight_kg_min NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS dogo_weight_kg_max NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS dogo_height_cm_min INTEGER,
ADD COLUMN IF NOT EXISTS dogo_height_cm_max INTEGER,
ADD COLUMN IF NOT EXISTS dogo_origin TEXT,
ADD COLUMN IF NOT EXISTS dogo_friendliness_to_dogs INTEGER CHECK (dogo_friendliness_to_dogs >= 0 AND dogo_friendliness_to_dogs <= 5),
ADD COLUMN IF NOT EXISTS dogo_friendliness_to_humans INTEGER CHECK (dogo_friendliness_to_humans >= 0 AND dogo_friendliness_to_humans <= 5),
ADD COLUMN IF NOT EXISTS dogo_last_updated TIMESTAMPTZ;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS breeds_breed_slug_idx ON breeds(breed_slug);
CREATE INDEX IF NOT EXISTS breeds_dogo_size_idx ON breeds(dogo_size);
CREATE INDEX IF NOT EXISTS breeds_dogo_energy_idx ON breeds(dogo_energy);

-- Create breed_raw table (stores raw HTML from Dogo)
CREATE TABLE IF NOT EXISTS breed_raw (
    id BIGSERIAL PRIMARY KEY,
    source_domain TEXT NOT NULL DEFAULT 'dogo.app',
    source_url TEXT NOT NULL UNIQUE,
    raw_html TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fingerprint TEXT NOT NULL,
    breed_slug TEXT  -- Link to breeds table
);

CREATE INDEX IF NOT EXISTS breed_raw_source_url_idx ON breed_raw(source_url);
CREATE INDEX IF NOT EXISTS breed_raw_fingerprint_idx ON breed_raw(fingerprint);
CREATE INDEX IF NOT EXISTS breed_raw_breed_slug_idx ON breed_raw(breed_slug);

-- Create breed_text_versions table (narrative content with versions)
CREATE TABLE IF NOT EXISTS breed_text_versions (
    id BIGSERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL,  -- References breeds.breed_slug
    language TEXT NOT NULL DEFAULT 'en',
    sections JSONB NOT NULL,   -- 5 sections: overview, temperament, training, grooming, health
    status text_status_enum NOT NULL DEFAULT 'draft',
    source TEXT NOT NULL DEFAULT 'dogo',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS breed_text_versions_breed_slug_idx ON breed_text_versions(breed_slug);
CREATE INDEX IF NOT EXISTS breed_text_versions_status_idx ON breed_text_versions(status);
CREATE INDEX IF NOT EXISTS breed_text_versions_language_idx ON breed_text_versions(language);

-- Unique constraint for one published version per breed/language
CREATE UNIQUE INDEX IF NOT EXISTS breed_text_versions_published_unique 
    ON breed_text_versions(breed_slug, language) 
    WHERE status = 'published';

-- Create breed_images table (hero images with attribution)
CREATE TABLE IF NOT EXISTS breed_images (
    id BIGSERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL,  -- References breeds.breed_slug
    image_public_url TEXT NOT NULL,
    image_hash TEXT,
    attribution TEXT DEFAULT 'dogo.app',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_primary BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS breed_images_breed_slug_idx ON breed_images(breed_slug);
CREATE INDEX IF NOT EXISTS breed_images_primary_idx ON breed_images(breed_slug, is_primary) WHERE is_primary = TRUE;

-- Create updated breeds_published view that combines existing and new Dogo data
CREATE OR REPLACE VIEW breeds_published AS
SELECT 
    -- Existing columns
    b.name_en,
    b.size_category,
    b.avg_male_weight_kg,
    b.avg_female_weight_kg,
    b.avg_height_cm,
    b.climate_tolerance,
    b.recommended_daily_exercise_min,
    b.activity_level_profile,
    b.weight_gain_risk_score,
    b.nutrition,
    b.primary_sources,
    b.name_ro,
    b.name_pl,
    b.name_hu,
    b.name_cs,
    b.care_profile,
    b.profile_version,
    b.last_generated_at,
    b.qa_status,
    
    -- New Dogo columns
    b.breed_slug,
    b.aliases,
    b.dogo_size,
    b.dogo_energy,
    b.dogo_coat_length,
    b.dogo_shedding,
    b.dogo_trainability,
    b.dogo_bark_level,
    b.dogo_lifespan_years_min,
    b.dogo_lifespan_years_max,
    b.dogo_weight_kg_min,
    b.dogo_weight_kg_max,
    b.dogo_height_cm_min,
    b.dogo_height_cm_max,
    b.dogo_origin,
    b.dogo_friendliness_to_dogs,
    b.dogo_friendliness_to_humans,
    b.dogo_last_updated,
    
    -- Latest published text content
    btv.sections as dogo_text_sections,
    btv.language as dogo_text_language,
    btv.created_at as dogo_text_published_at,
    
    -- Primary image
    bi.image_public_url as dogo_primary_image_url,
    bi.attribution as dogo_image_attribution
    
FROM breeds b
LEFT JOIN breed_text_versions btv ON (
    b.breed_slug = btv.breed_slug 
    AND btv.status = 'published' 
    AND btv.language = 'en'
)
LEFT JOIN breed_images bi ON (
    b.breed_slug = bi.breed_slug 
    AND bi.is_primary = TRUE
);

-- Show all tables
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE 'breed%' OR table_name = 'breeds_published')
ORDER BY table_name;