-- Breed Database Schema for Dogo Scraper
-- Execute this SQL in your Supabase dashboard

-- Create enum types for controlled vocabularies
DO $$ BEGIN
    CREATE TYPE size_enum AS ENUM ('tiny', 'small', 'medium', 'large', 'giant');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE energy_enum AS ENUM ('low', 'moderate', 'high', 'very_high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE coat_length_enum AS ENUM ('short', 'medium', 'long');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE shedding_enum AS ENUM ('minimal', 'low', 'moderate', 'high', 'very_high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE trainability_enum AS ENUM ('challenging', 'moderate', 'easy', 'very_easy');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE bark_level_enum AS ENUM ('quiet', 'occasional', 'moderate', 'frequent', 'very_vocal');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE text_status_enum AS ENUM ('draft', 'published');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create breed_raw table (stores raw HTML from Dogo)
CREATE TABLE IF NOT EXISTS breed_raw (
    id BIGSERIAL PRIMARY KEY,
    source_domain TEXT NOT NULL DEFAULT 'dogo.app',
    source_url TEXT NOT NULL UNIQUE,
    raw_html TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fingerprint TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS breed_raw_source_url_idx ON breed_raw(source_url);
CREATE INDEX IF NOT EXISTS breed_raw_fingerprint_idx ON breed_raw(fingerprint);

-- Create breeds table (normalized breed facts)
CREATE TABLE IF NOT EXISTS breeds (
    id BIGSERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    size size_enum,
    energy energy_enum,
    coat_length coat_length_enum,
    shedding shedding_enum,
    trainability trainability_enum,
    bark_level bark_level_enum,
    lifespan_years_min INTEGER,
    lifespan_years_max INTEGER,
    weight_kg_min NUMERIC(5,2),
    weight_kg_max NUMERIC(5,2),
    height_cm_min INTEGER,
    height_cm_max INTEGER,
    origin TEXT,
    friendliness_to_dogs INTEGER CHECK (friendliness_to_dogs >= 0 AND friendliness_to_dogs <= 5),
    friendliness_to_humans INTEGER CHECK (friendliness_to_humans >= 0 AND friendliness_to_humans <= 5),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS breeds_breed_slug_idx ON breeds(breed_slug);
CREATE INDEX IF NOT EXISTS breeds_size_idx ON breeds(size);
CREATE INDEX IF NOT EXISTS breeds_energy_idx ON breeds(energy);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_breeds_updated_at ON breeds;
CREATE TRIGGER update_breeds_updated_at 
    BEFORE UPDATE ON breeds 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create breed_text_versions table (narrative content with versions)
CREATE TABLE IF NOT EXISTS breed_text_versions (
    id BIGSERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL REFERENCES breeds(breed_slug) ON DELETE CASCADE,
    language TEXT NOT NULL DEFAULT 'en',
    sections JSONB NOT NULL,
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
    breed_slug TEXT NOT NULL REFERENCES breeds(breed_slug) ON DELETE CASCADE,
    image_public_url TEXT NOT NULL,
    image_hash TEXT,
    attribution TEXT DEFAULT 'dogo.app',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_primary BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS breed_images_breed_slug_idx ON breed_images(breed_slug);
CREATE INDEX IF NOT EXISTS breed_images_primary_idx ON breed_images(breed_slug, is_primary) WHERE is_primary = TRUE;

-- Create breeds_published view (clean API access)
CREATE OR REPLACE VIEW breeds_published AS
SELECT 
    b.breed_slug,
    b.display_name,
    b.aliases,
    b.size,
    b.energy,
    b.coat_length,
    b.shedding,
    b.trainability,
    b.bark_level,
    b.lifespan_years_min,
    b.lifespan_years_max,
    b.weight_kg_min,
    b.weight_kg_max,
    b.height_cm_min,
    b.height_cm_max,
    b.origin,
    b.friendliness_to_dogs,
    b.friendliness_to_humans,
    b.updated_at,
    -- Latest published text content
    btv.sections as text_sections,
    btv.language as text_language,
    btv.created_at as text_published_at,
    -- Primary image
    bi.image_public_url as primary_image_url,
    bi.attribution as image_attribution
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

-- Show created tables
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE 'breed%' OR table_name = 'breeds_published')
ORDER BY table_name;