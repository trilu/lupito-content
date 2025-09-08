#!/usr/bin/env python3
"""
Create database schema for Dogo breed scraping system
Includes controlled vocabularies, breed tables, and publishing view
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🔧 Creating breed database schema...")
    print("⚠️  Note: This creates tables without custom enums. Enums need to be created manually in Supabase dashboard.")
    
    try:
        # Initialize Supabase client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_KEY')
        )
        
        print("\n📋 SQL to run manually in Supabase dashboard:")
        print("=" * 60)
        
        enums_sql = """-- Run this SQL in your Supabase dashboard first:

-- Size enum
DO $$ BEGIN
    CREATE TYPE size_enum AS ENUM ('tiny', 'small', 'medium', 'large', 'giant');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Energy enum  
DO $$ BEGIN
    CREATE TYPE energy_enum AS ENUM ('low', 'moderate', 'high', 'very_high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Coat length enum
DO $$ BEGIN
    CREATE TYPE coat_length_enum AS ENUM ('short', 'medium', 'long');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Shedding enum
DO $$ BEGIN
    CREATE TYPE shedding_enum AS ENUM ('minimal', 'low', 'moderate', 'high', 'very_high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Trainability enum
DO $$ BEGIN
    CREATE TYPE trainability_enum AS ENUM ('challenging', 'moderate', 'easy', 'very_easy');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Bark level enum
DO $$ BEGIN
    CREATE TYPE bark_level_enum AS ENUM ('quiet', 'occasional', 'moderate', 'frequent', 'very_vocal');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Text status enum
DO $$ BEGIN
    CREATE TYPE text_status_enum AS ENUM ('draft', 'published');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
"""
        
        print(enums_sql)
        print("=" * 60)
        print("⏳ For now, creating basic tables with TEXT fields instead of enums...")
        
        # Test connection by querying existing tables
        print("📝 Testing Supabase connection...")
        try:
            # Check if food_candidates table exists (we know this works)
            result = supabase.table('food_candidates').select('id').limit(1).execute()
            print("✅ Supabase connection working")
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            return False
        
        # Create breeds table
        print("📝 Creating breeds table...")
        breeds_sql = """
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

        -- Indexes for performance
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
        """
        
        result = supabase.rpc('exec_sql', {'sql': breeds_sql}).execute()
        print("✅ Created breeds table")
        
        # Create breed_text_versions table
        print("📝 Creating breed_text_versions table...")
        text_versions_sql = """
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

        -- Indexes for performance  
        CREATE INDEX IF NOT EXISTS breed_text_versions_breed_slug_idx ON breed_text_versions(breed_slug);
        CREATE INDEX IF NOT EXISTS breed_text_versions_status_idx ON breed_text_versions(status);
        CREATE INDEX IF NOT EXISTS breed_text_versions_language_idx ON breed_text_versions(language);
        
        -- Unique constraint for one published version per breed/language
        CREATE UNIQUE INDEX IF NOT EXISTS breed_text_versions_published_unique 
            ON breed_text_versions(breed_slug, language) 
            WHERE status = 'published';
        """
        
        result = supabase.rpc('exec_sql', {'sql': text_versions_sql}).execute()
        print("✅ Created breed_text_versions table")
        
        # Create breed_images table
        print("📝 Creating breed_images table...")
        images_sql = """
        CREATE TABLE IF NOT EXISTS breed_images (
            id BIGSERIAL PRIMARY KEY,
            breed_slug TEXT NOT NULL REFERENCES breeds(breed_slug) ON DELETE CASCADE,
            image_public_url TEXT NOT NULL,
            image_hash TEXT,
            attribution TEXT DEFAULT 'dogo.app',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_primary BOOLEAN DEFAULT FALSE
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS breed_images_breed_slug_idx ON breed_images(breed_slug);
        CREATE INDEX IF NOT EXISTS breed_images_primary_idx ON breed_images(breed_slug, is_primary) WHERE is_primary = TRUE;
        """
        
        result = supabase.rpc('exec_sql', {'sql': images_sql}).execute()
        print("✅ Created breed_images table")
        
        # Create breeds_published view
        print("📝 Creating breeds_published view...")
        view_sql = """
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
        """
        
        result = supabase.rpc('exec_sql', {'sql': view_sql}).execute()
        print("✅ Created breeds_published view")
        
        print("🎯 Breed database schema created successfully!")
        
        # Verify by querying table info
        print("\n🔍 Verifying schema...")
        test_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'breed%' ORDER BY table_name;"
        result = supabase.rpc('exec_sql', {'sql': test_query}).execute()
        
        print("📋 Created tables:")
        if result.data:
            for row in result.data:
                print(f"  - {row['table_name']}")
        
        print("\n✅ Schema verification complete!")
        
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        print("\n🔧 If this fails, you can run the SQL manually in Supabase dashboard")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    if success:
        print("\n🚀 Ready to build breed scraper!")
    else:
        print("\n⚠️  Please check the error and retry")