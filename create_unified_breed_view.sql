-- ============================================
-- UNIFIED BREED DATA VIEW FOR API
-- Consolidates all breed information from multiple tables
-- into a single, comprehensive view for API consumption
-- ============================================

-- First check if the view already exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'breeds_unified_api') THEN
        DROP VIEW breeds_unified_api CASCADE;
        RAISE NOTICE 'Dropped existing breeds_unified_api view';
    END IF;
END $$;

-- Create the comprehensive unified view
CREATE VIEW breeds_unified_api AS
SELECT
    -- ===== CORE IDENTIFICATION =====
    bp.id,
    bp.breed_slug,
    bp.display_name,
    bp.aliases,

    -- ===== PHYSICAL CHARACTERISTICS =====
    bp.size_category,
    bp.adult_weight_min_kg,
    bp.adult_weight_max_kg,
    bp.adult_weight_avg_kg,
    bp.height_min_cm,
    bp.height_max_cm,
    bp.lifespan_min_years,
    bp.lifespan_max_years,
    bp.lifespan_avg_years,

    -- ===== LIFE STAGES =====
    bp.growth_end_months,
    bp.senior_start_months,

    -- ===== BEHAVIORAL TRAITS =====
    bp.energy,
    bp.trainability,
    bp.coat_length,
    bp.shedding,
    bp.bark_level,
    bp.friendliness_to_dogs,
    bp.friendliness_to_humans,

    -- ===== ORIGIN & HISTORY =====
    bp.origin,
    bcc.history,
    bcc.history_brief,
    bcc.introduction,

    -- ===== PERSONALITY & TEMPERAMENT =====
    bcc.personality_description,
    bcc.personality_traits,
    bcc.temperament,
    bcc.good_with_children,
    bcc.good_with_pets,
    bcc.intelligence_noted,

    -- ===== CARE REQUIREMENTS =====
    bcc.general_care,
    bcc.grooming_needs,
    bcc.grooming_frequency,
    bcc.exercise_needs_detail,
    bcc.exercise_level,
    bcc.training_tips,

    -- ===== HEALTH INFORMATION =====
    bcc.health_issues,

    -- ===== PHYSICAL APPEARANCE =====
    bcc.coat,
    bcc.colors,
    bcc.color_varieties,

    -- ===== FUN & ENRICHMENT CONTENT =====
    bcc.fun_facts,
    bcc.has_world_records,
    bcc.working_roles,

    -- ===== BREED STANDARDS =====
    bcc.breed_standard,
    bcc.recognized_by,

    -- ===== DATA QUALITY & METADATA =====
    bp.data_quality_grade,
    bp.conflict_flags,

    -- ===== PROVENANCE TRACKING =====
    bp.size_from,
    bp.weight_from,
    bp.height_from,
    bp.lifespan_from,
    bp.age_bounds_from,
    bp.override_reason,

    -- ===== CONTENT SOURCES =====
    bcc.wikipedia_url,
    bcc.scraped_at,

    -- ===== TIMESTAMPS =====
    bp.created_at,
    bp.updated_at,
    bcc.updated_at as content_updated_at,

    -- ===== COMPUTED FIELDS =====
    -- Content completeness score (0-100)
    ROUND(
        (
            CASE WHEN bp.size_category IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bp.adult_weight_avg_kg IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bp.energy IS NOT NULL AND bp.energy != 'moderate' THEN 10 ELSE 0 END +
            CASE WHEN bcc.personality_description IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bcc.general_care IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bcc.grooming_needs IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bcc.exercise_needs_detail IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bcc.health_issues IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN array_length(bcc.fun_facts, 1) > 0 THEN 10 ELSE 0 END +
            CASE WHEN array_length(bcc.working_roles, 1) > 0 THEN 10 ELSE 0 END
        )
    , 0) AS content_completeness_score,

    -- Has rich content flag
    CASE
        WHEN bcc.personality_description IS NOT NULL
            AND bcc.general_care IS NOT NULL
            AND (array_length(bcc.fun_facts, 1) > 0 OR array_length(bcc.working_roles, 1) > 0)
        THEN true
        ELSE false
    END AS has_rich_content,

    -- Care content word count
    CASE
        WHEN bcc.general_care IS NOT NULL
        THEN array_length(string_to_array(bcc.general_care, ' '), 1)
        ELSE 0
    END AS care_content_word_count,

    -- Size category display name
    CASE bp.size_category
        WHEN 'xs' THEN 'Extra Small'
        WHEN 's' THEN 'Small'
        WHEN 'm' THEN 'Medium'
        WHEN 'l' THEN 'Large'
        WHEN 'xl' THEN 'Extra Large'
        ELSE 'Unknown'
    END AS size_category_display,

    -- Energy level display name
    CASE bp.energy
        WHEN 'low' THEN 'Low Energy'
        WHEN 'moderate' THEN 'Moderate Energy'
        WHEN 'high' THEN 'High Energy'
        WHEN 'very_high' THEN 'Very High Energy'
        ELSE 'Moderate Energy'
    END AS energy_level_display

FROM breeds_published bp
LEFT JOIN breeds_comprehensive_content bcc
    ON bp.breed_slug = bcc.breed_slug
WHERE
    -- Only include breeds with good data quality
    bp.data_quality_grade IN ('A+', 'A', 'B')
ORDER BY bp.display_name;

-- Note: Indexes should be created on the underlying tables, not views
-- The breeds_published view already uses indexes from breeds_details table
-- Check and create indexes on base tables if needed

DO $$
BEGIN
    -- Create index on breeds_details if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_breeds_details_slug') THEN
        CREATE INDEX idx_breeds_details_slug ON breeds_details(breed_slug);
        RAISE NOTICE 'Created index on breeds_details.breed_slug';
    END IF;

    -- Create index on breeds_comprehensive_content if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_breeds_comprehensive_content_slug') THEN
        CREATE INDEX idx_breeds_comprehensive_content_slug ON breeds_comprehensive_content(breed_slug);
        RAISE NOTICE 'Created index on breeds_comprehensive_content.breed_slug';
    END IF;
END $$;

-- Grant permissions
GRANT SELECT ON breeds_unified_api TO authenticated;
GRANT SELECT ON breeds_unified_api TO anon;
GRANT SELECT ON breeds_unified_api TO service_role;

-- ============================================
-- HELPER FUNCTIONS FOR API
-- ============================================

-- Function to get a single breed with all details
CREATE OR REPLACE FUNCTION get_breed_complete(p_breed_slug TEXT)
RETURNS SETOF breeds_unified_api
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM breeds_unified_api
    WHERE breed_slug = p_breed_slug
    LIMIT 1;
END;
$$;

-- Function to search breeds with filters
CREATE OR REPLACE FUNCTION search_breeds_complete(
    p_size_categories TEXT[] DEFAULT NULL,
    p_energy_levels TEXT[] DEFAULT NULL,
    p_good_with_children BOOLEAN DEFAULT NULL,
    p_good_with_pets BOOLEAN DEFAULT NULL,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    breed_slug TEXT,
    display_name TEXT,
    size_category TEXT,
    energy TEXT,
    good_with_children BOOLEAN,
    good_with_pets BOOLEAN,
    content_completeness_score NUMERIC,
    has_rich_content BOOLEAN
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        b.breed_slug,
        b.display_name,
        b.size_category,
        b.energy,
        b.good_with_children,
        b.good_with_pets,
        b.content_completeness_score,
        b.has_rich_content
    FROM breeds_unified_api b
    WHERE
        (p_size_categories IS NULL OR b.size_category = ANY(p_size_categories))
        AND (p_energy_levels IS NULL OR b.energy = ANY(p_energy_levels))
        AND (p_good_with_children IS NULL OR b.good_with_children = p_good_with_children)
        AND (p_good_with_pets IS NULL OR b.good_with_pets = p_good_with_pets)
    ORDER BY b.content_completeness_score DESC, b.display_name
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Function to get breed recommendations based on characteristics
CREATE OR REPLACE FUNCTION get_similar_breeds(
    p_breed_slug TEXT,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    breed_slug TEXT,
    display_name TEXT,
    similarity_score NUMERIC,
    size_match BOOLEAN,
    energy_match BOOLEAN,
    temperament_match BOOLEAN
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    source_breed RECORD;
BEGIN
    -- Get the source breed characteristics
    SELECT
        size_category,
        energy,
        good_with_children,
        good_with_pets,
        trainability
    INTO source_breed
    FROM breeds_unified_api
    WHERE breed_slug = p_breed_slug
    LIMIT 1;

    -- Find similar breeds
    RETURN QUERY
    SELECT
        b.breed_slug,
        b.display_name,
        -- Calculate similarity score (0-100)
        ROUND(
            (
                CASE WHEN b.size_category = source_breed.size_category THEN 25 ELSE 0 END +
                CASE WHEN b.energy = source_breed.energy THEN 25 ELSE 0 END +
                CASE WHEN b.good_with_children = source_breed.good_with_children THEN 15 ELSE 0 END +
                CASE WHEN b.good_with_pets = source_breed.good_with_pets THEN 15 ELSE 0 END +
                CASE WHEN b.trainability = source_breed.trainability THEN 20 ELSE 0 END
            )::NUMERIC
        , 0) AS similarity_score,
        b.size_category = source_breed.size_category AS size_match,
        b.energy = source_breed.energy AS energy_match,
        (b.good_with_children = source_breed.good_with_children
            AND b.good_with_pets = source_breed.good_with_pets) AS temperament_match
    FROM breeds_unified_api b
    WHERE b.breed_slug != p_breed_slug
    ORDER BY similarity_score DESC
    LIMIT p_limit;
END;
$$;

-- ============================================
-- MONITORING & STATISTICS VIEW
-- ============================================

CREATE OR REPLACE VIEW breeds_api_statistics AS
SELECT
    COUNT(*) as total_breeds,
    COUNT(CASE WHEN has_rich_content THEN 1 END) as breeds_with_rich_content,
    COUNT(CASE WHEN content_completeness_score >= 80 THEN 1 END) as high_quality_breeds,
    COUNT(CASE WHEN content_completeness_score >= 50 AND content_completeness_score < 80 THEN 1 END) as medium_quality_breeds,
    COUNT(CASE WHEN content_completeness_score < 50 THEN 1 END) as low_quality_breeds,
    ROUND(AVG(content_completeness_score), 1) as avg_completeness_score,
    COUNT(CASE WHEN personality_description IS NOT NULL THEN 1 END) as with_personality,
    COUNT(CASE WHEN general_care IS NOT NULL THEN 1 END) as with_care_content,
    COUNT(CASE WHEN array_length(fun_facts, 1) > 0 THEN 1 END) as with_fun_facts,
    COUNT(CASE WHEN health_issues IS NOT NULL THEN 1 END) as with_health_info
FROM breeds_unified_api;

-- Grant permissions for statistics
GRANT SELECT ON breeds_api_statistics TO authenticated;
GRANT SELECT ON breeds_api_statistics TO anon;

-- ============================================
-- USAGE EXAMPLES FOR API TEAM
-- ============================================

COMMENT ON VIEW breeds_unified_api IS 'Unified breed data view consolidating all breed information for API consumption. Use this as the single source of truth for breed pages.';

COMMENT ON FUNCTION get_breed_complete IS 'Get complete breed information by breed_slug. Example: SELECT * FROM get_breed_complete(''golden-retriever'');';

COMMENT ON FUNCTION search_breeds_complete IS 'Search breeds with multiple filters. Example: SELECT * FROM search_breeds_complete(ARRAY[''l'',''xl''], ARRAY[''high''], true, true, 10, 0);';

COMMENT ON FUNCTION get_similar_breeds IS 'Get breeds similar to a given breed. Example: SELECT * FROM get_similar_breeds(''golden-retriever'', 5);';

-- Verification query
SELECT
    'Unified breed view created successfully' as status,
    COUNT(*) as total_breeds,
    ROUND(AVG(content_completeness_score), 1) as avg_completeness,
    COUNT(CASE WHEN has_rich_content THEN 1 END) as rich_content_count
FROM breeds_unified_api;