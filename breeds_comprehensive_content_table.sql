-- ============================================
-- COMPREHENSIVE BREED CONTENT TABLE
-- For storing all the rich Wikipedia content
-- ============================================

CREATE TABLE IF NOT EXISTS breeds_comprehensive_content (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL UNIQUE,

    -- Introduction and History
    introduction TEXT,
    history TEXT,
    history_brief TEXT,

    -- Personality and Temperament
    personality_description TEXT,
    personality_traits TEXT[], -- Array of personality traits
    temperament TEXT,
    good_with_children BOOLEAN,
    good_with_pets BOOLEAN,
    intelligence_noted BOOLEAN,

    -- Care Requirements
    grooming_needs TEXT,
    grooming_frequency TEXT, -- 'daily', 'weekly', 'minimal'
    exercise_needs_detail TEXT,
    exercise_level TEXT, -- 'high', 'moderate', 'low'
    training_tips TEXT,
    general_care TEXT,

    -- Fun Facts and Trivia
    fun_facts TEXT[], -- Array of fun facts
    has_world_records BOOLEAN,
    working_roles TEXT[], -- Array of working roles (police, service, etc.)

    -- Breed Standards
    breed_standard TEXT,
    recognized_by TEXT[], -- Array of kennel clubs
    color_varieties TEXT,

    -- Health Information (from existing extraction)
    health_issues TEXT,

    -- Physical Characteristics (enhanced)
    coat TEXT,
    colors TEXT,

    -- Metadata
    wikipedia_url TEXT,
    gcs_html_path TEXT,
    gcs_json_path TEXT,
    scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_breeds_comprehensive_slug ON breeds_comprehensive_content(breed_slug);
CREATE INDEX IF NOT EXISTS idx_breeds_comprehensive_children ON breeds_comprehensive_content(good_with_children);
CREATE INDEX IF NOT EXISTS idx_breeds_comprehensive_pets ON breeds_comprehensive_content(good_with_pets);
CREATE INDEX IF NOT EXISTS idx_breeds_comprehensive_exercise ON breeds_comprehensive_content(exercise_level);

-- Grant permissions
GRANT ALL ON breeds_comprehensive_content TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE breeds_comprehensive_content_id_seq TO authenticated;

-- Create a view that combines everything for easy access
CREATE OR REPLACE VIEW breeds_complete_profile AS
SELECT
    bp.breed_slug,
    bp.display_name,
    bp.aliases,

    -- Physical characteristics
    bp.size_category,
    bp.adult_weight_min_kg,
    bp.adult_weight_max_kg,
    bp.adult_weight_avg_kg,
    bp.height_min_cm,
    bp.height_max_cm,
    bp.lifespan_min_years,
    bp.lifespan_max_years,
    bp.lifespan_avg_years,

    -- Behavioral characteristics
    bp.energy,
    bp.trainability,
    bp.bark_level,
    bp.shedding,
    bp.coat_length,

    -- Comprehensive content
    bcc.introduction,
    bcc.history_brief,
    bcc.personality_description,
    bcc.personality_traits,
    bcc.good_with_children,
    bcc.good_with_pets,
    bcc.intelligence_noted,
    bcc.grooming_frequency,
    bcc.exercise_level,
    bcc.training_tips,
    bcc.fun_facts,
    bcc.working_roles,
    bcc.recognized_by,

    -- Metadata
    bp.data_quality_grade,
    bp.updated_at as basic_data_updated,
    bcc.updated_at as content_updated
FROM
    breeds_published bp
LEFT JOIN
    breeds_comprehensive_content bcc ON bp.breed_slug = bcc.breed_slug;

-- Grant view permissions
GRANT SELECT ON breeds_complete_profile TO authenticated;