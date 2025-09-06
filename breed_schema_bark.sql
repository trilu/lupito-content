-- Breed Details Schema for Bark Scraper
-- Creates separate breeds_details table to preserve existing breeds table
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

-- Create breeds_details table (new detailed breed information)
CREATE TABLE IF NOT EXISTS breeds_details (
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS breeds_details_breed_slug_idx ON breeds_details(breed_slug);
CREATE INDEX IF NOT EXISTS breeds_details_size_idx ON breeds_details(size);
CREATE INDEX IF NOT EXISTS breeds_details_energy_idx ON breeds_details(energy);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_breeds_details_updated_at ON breeds_details;
CREATE TRIGGER update_breeds_details_updated_at 
    BEFORE UPDATE ON breeds_details 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create breed_raw table (stores raw HTML)
CREATE TABLE IF NOT EXISTS breed_raw (
    id BIGSERIAL PRIMARY KEY,
    source_domain TEXT NOT NULL DEFAULT 'external',
    source_url TEXT NOT NULL UNIQUE,
    raw_html TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fingerprint TEXT NOT NULL,
    breed_slug TEXT REFERENCES breeds_details(breed_slug)
);

CREATE INDEX IF NOT EXISTS breed_raw_source_url_idx ON breed_raw(source_url);
CREATE INDEX IF NOT EXISTS breed_raw_fingerprint_idx ON breed_raw(fingerprint);
CREATE INDEX IF NOT EXISTS breed_raw_breed_slug_idx ON breed_raw(breed_slug);

-- Create breed_text_versions table (narrative content with versions)
CREATE TABLE IF NOT EXISTS breed_text_versions (
    id BIGSERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL REFERENCES breeds_details(breed_slug) ON DELETE CASCADE,
    language TEXT NOT NULL DEFAULT 'en',
    sections JSONB NOT NULL,   -- 5 sections: overview, temperament, training, grooming, health
    status text_status_enum NOT NULL DEFAULT 'draft',
    source TEXT NOT NULL DEFAULT 'bark',
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
    breed_slug TEXT NOT NULL REFERENCES breeds_details(breed_slug) ON DELETE CASCADE,
    image_public_url TEXT NOT NULL,
    image_hash TEXT,
    attribution TEXT DEFAULT 'bark',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_primary BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS breed_images_breed_slug_idx ON breed_images(breed_slug);
CREATE INDEX IF NOT EXISTS breed_images_primary_idx ON breed_images(breed_slug, is_primary) WHERE is_primary = TRUE;

-- Create breeds_published view that combines breed details with published content
CREATE OR REPLACE VIEW breeds_published AS
SELECT 
    -- From breeds_details table
    bd.breed_slug,
    bd.display_name,
    bd.aliases,
    bd.size,
    bd.energy,
    bd.coat_length,
    bd.shedding,
    bd.trainability,
    bd.bark_level,
    bd.lifespan_years_min,
    bd.lifespan_years_max,
    bd.weight_kg_min,
    bd.weight_kg_max,
    bd.height_cm_min,
    bd.height_cm_max,
    bd.origin,
    bd.friendliness_to_dogs,
    bd.friendliness_to_humans,
    bd.updated_at,
    
    -- Latest published text content
    btv.sections as text_sections,
    btv.language as text_language,
    btv.created_at as text_published_at,
    
    -- Primary image
    bi.image_public_url as primary_image_url,
    bi.attribution as image_attribution
    
FROM breeds_details bd
LEFT JOIN breed_text_versions btv ON (
    bd.breed_slug = btv.breed_slug 
    AND btv.status = 'published' 
    AND btv.language = 'en'
)
LEFT JOIN breed_images bi ON (
    bd.breed_slug = bi.breed_slug 
    AND bi.is_primary = TRUE
);

-- Create breeds_full view that combines existing breeds table with new breeds_details
CREATE OR REPLACE VIEW breeds_full AS
SELECT 
    -- From existing breeds table
    b.name_en,
    b.size_category as existing_size,
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
    
    -- From breeds_details table
    bd.breed_slug,
    bd.display_name,
    bd.aliases,
    bd.size as detailed_size,
    bd.energy,
    bd.coat_length,
    bd.shedding,
    bd.trainability,
    bd.bark_level,
    bd.lifespan_years_min,
    bd.lifespan_years_max,
    bd.weight_kg_min as detailed_weight_kg_min,
    bd.weight_kg_max as detailed_weight_kg_max,
    bd.height_cm_min as detailed_height_cm_min,
    bd.height_cm_max as detailed_height_cm_max,
    bd.origin,
    bd.friendliness_to_dogs,
    bd.friendliness_to_humans
    
FROM breeds b
LEFT JOIN breeds_details bd ON LOWER(b.name_en) = LOWER(bd.display_name);

-- Show all tables
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE 'breed%' OR table_name = 'breeds_published' OR table_name = 'breeds_full')
ORDER BY table_name;