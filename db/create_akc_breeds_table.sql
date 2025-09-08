-- ============================================================================
-- Create AKC Breeds Table
-- ============================================================================
-- Separate table for AKC breed data that will be merged later
-- This allows testing and iteration without affecting existing breeds_details
-- ============================================================================

-- Drop table if exists (for clean setup)
DROP TABLE IF EXISTS akc_breeds CASCADE;

-- Create AKC breeds table with comprehensive schema
CREATE TABLE akc_breeds (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Breed identification
    breed_slug VARCHAR(255) UNIQUE NOT NULL,  -- URL slug (e.g., "german-shepherd-dog")
    display_name VARCHAR(255) NOT NULL,       -- Display name (e.g., "German Shepherd Dog")
    akc_url VARCHAR(500),                     -- Source URL from AKC
    
    -- Physical characteristics
    size VARCHAR(50),                         -- small, medium, large, giant
    height_cm_min NUMERIC(5,1),              -- Minimum height in cm
    height_cm_max NUMERIC(5,1),              -- Maximum height in cm
    weight_kg_min NUMERIC(5,1),              -- Minimum weight in kg
    weight_kg_max NUMERIC(5,1),              -- Maximum weight in kg
    
    -- Life expectancy
    lifespan_years_min INTEGER,
    lifespan_years_max INTEGER,
    
    -- Breed characteristics (normalized)
    energy VARCHAR(50),                       -- low, moderate, high, very high
    coat_length VARCHAR(50),                  -- short, medium, long
    shedding VARCHAR(50),                     -- low, moderate, high
    trainability VARCHAR(50),                 -- easy, moderate, challenging
    bark_level VARCHAR(50),                   -- low, moderate, high
    
    -- Temperament scores
    friendliness_to_dogs INTEGER CHECK (friendliness_to_dogs BETWEEN 1 AND 5),
    friendliness_to_humans INTEGER CHECK (friendliness_to_humans BETWEEN 1 AND 5),
    good_with_children BOOLEAN,
    good_with_other_pets BOOLEAN,
    
    -- Origin and history
    origin VARCHAR(255),                      -- Country/region of origin
    breed_group VARCHAR(100),                 -- AKC breed group (e.g., "Working", "Sporting")
    
    -- Comprehensive content (JSON)
    comprehensive_content JSONB,              -- All extracted content sections
    raw_traits JSONB,                         -- Raw traits as extracted from AKC
    
    -- Metadata
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    extraction_status VARCHAR(50),            -- success, partial, failed
    extraction_notes TEXT,                    -- Any notes about extraction issues
    
    -- Quality tracking
    data_completeness_score INTEGER,          -- 0-100 score of how complete the data is
    has_physical_data BOOLEAN DEFAULT FALSE,  -- Has height/weight data
    has_temperament_data BOOLEAN DEFAULT FALSE, -- Has temperament scores
    has_content BOOLEAN DEFAULT FALSE         -- Has comprehensive content
);

-- Create indexes for performance
CREATE INDEX idx_akc_breeds_slug ON akc_breeds(breed_slug);
CREATE INDEX idx_akc_breeds_size ON akc_breeds(size);
CREATE INDEX idx_akc_breeds_energy ON akc_breeds(energy);
CREATE INDEX idx_akc_breeds_breed_group ON akc_breeds(breed_group);
CREATE INDEX idx_akc_breeds_extraction_status ON akc_breeds(extraction_status);
CREATE INDEX idx_akc_breeds_data_completeness ON akc_breeds(data_completeness_score);

-- Create GIN index for JSONB columns
CREATE INDEX idx_akc_breeds_content_gin ON akc_breeds USING gin(comprehensive_content);
CREATE INDEX idx_akc_breeds_traits_gin ON akc_breeds USING gin(raw_traits);

-- ============================================================================
-- Helper Views
-- ============================================================================

-- View for breeds with complete data
CREATE OR REPLACE VIEW akc_breeds_complete AS
SELECT *
FROM akc_breeds
WHERE data_completeness_score >= 70
  AND has_physical_data = TRUE
  AND has_content = TRUE;

-- View for breeds needing enhancement
CREATE OR REPLACE VIEW akc_breeds_incomplete AS
SELECT 
    breed_slug,
    display_name,
    data_completeness_score,
    has_physical_data,
    has_temperament_data,
    has_content,
    extraction_notes
FROM akc_breeds
WHERE data_completeness_score < 70
   OR has_physical_data = FALSE
   OR has_content = FALSE
ORDER BY data_completeness_score ASC;

-- View for matching with existing breeds
CREATE OR REPLACE VIEW akc_breeds_matching AS
SELECT 
    a.breed_slug as akc_slug,
    a.display_name as akc_name,
    b.name_en as existing_breed_name,
    CASE 
        WHEN LOWER(REPLACE(b.name_en, ' ', '-')) = a.breed_slug THEN 'exact'
        WHEN LOWER(b.name_en) LIKE '%' || LOWER(a.display_name) || '%' THEN 'partial'
        ELSE 'review'
    END as match_quality
FROM akc_breeds a
LEFT JOIN breeds b ON LOWER(REPLACE(b.name_en, ' ', '-')) = a.breed_slug
   OR LOWER(b.name_en) = LOWER(a.display_name);

-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Function to calculate data completeness score
CREATE OR REPLACE FUNCTION calculate_akc_breed_completeness(breed_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    score INTEGER := 0;
    breed_record akc_breeds%ROWTYPE;
BEGIN
    SELECT * INTO breed_record FROM akc_breeds WHERE id = breed_id;
    
    -- Basic fields (40 points)
    IF breed_record.display_name IS NOT NULL THEN score := score + 5; END IF;
    IF breed_record.breed_slug IS NOT NULL THEN score := score + 5; END IF;
    IF breed_record.size IS NOT NULL THEN score := score + 10; END IF;
    IF breed_record.energy IS NOT NULL THEN score := score + 10; END IF;
    IF breed_record.breed_group IS NOT NULL THEN score := score + 10; END IF;
    
    -- Physical data (30 points)
    IF breed_record.height_cm_max IS NOT NULL THEN score := score + 10; END IF;
    IF breed_record.weight_kg_max IS NOT NULL THEN score := score + 10; END IF;
    IF breed_record.lifespan_years_max IS NOT NULL THEN score := score + 10; END IF;
    
    -- Characteristics (20 points)
    IF breed_record.coat_length IS NOT NULL THEN score := score + 5; END IF;
    IF breed_record.shedding IS NOT NULL THEN score := score + 5; END IF;
    IF breed_record.trainability IS NOT NULL THEN score := score + 5; END IF;
    IF breed_record.bark_level IS NOT NULL THEN score := score + 5; END IF;
    
    -- Content (10 points)
    IF breed_record.comprehensive_content IS NOT NULL 
       AND jsonb_typeof(breed_record.comprehensive_content) != 'null' THEN 
        score := score + 10; 
    END IF;
    
    RETURN score;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update completeness score on insert/update
CREATE OR REPLACE FUNCTION update_akc_breed_completeness()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_completeness_score := calculate_akc_breed_completeness(NEW.id);
    NEW.has_physical_data := (NEW.height_cm_max IS NOT NULL OR NEW.weight_kg_max IS NOT NULL);
    NEW.has_temperament_data := (NEW.friendliness_to_dogs IS NOT NULL OR NEW.friendliness_to_humans IS NOT NULL);
    NEW.has_content := (NEW.comprehensive_content IS NOT NULL AND jsonb_typeof(NEW.comprehensive_content) != 'null');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_akc_breed_completeness
BEFORE INSERT OR UPDATE ON akc_breeds
FOR EACH ROW
EXECUTE FUNCTION update_akc_breed_completeness();

-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Check total breeds
-- SELECT COUNT(*) as total_breeds FROM akc_breeds;

-- Check data quality
-- SELECT 
--     COUNT(*) as total,
--     AVG(data_completeness_score) as avg_completeness,
--     SUM(CASE WHEN has_physical_data THEN 1 ELSE 0 END) as with_physical_data,
--     SUM(CASE WHEN has_temperament_data THEN 1 ELSE 0 END) as with_temperament,
--     SUM(CASE WHEN has_content THEN 1 ELSE 0 END) as with_content
-- FROM akc_breeds;

-- Find breeds ready for merging
-- SELECT breed_slug, display_name, data_completeness_score
-- FROM akc_breeds
-- WHERE data_completeness_score >= 70
-- ORDER BY display_name;

-- ============================================================================
-- Grant Permissions
-- ============================================================================
GRANT SELECT ON akc_breeds TO authenticated;
GRANT SELECT ON akc_breeds TO anon;
GRANT ALL ON akc_breeds TO service_role;
GRANT SELECT ON akc_breeds_complete TO authenticated;
GRANT SELECT ON akc_breeds_incomplete TO authenticated;
GRANT SELECT ON akc_breeds_matching TO authenticated;