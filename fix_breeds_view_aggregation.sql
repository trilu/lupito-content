-- ============================================
-- FIX BREEDS_UNIFIED_API VIEW TO AGGREGATE FROM BOTH TABLES
-- This script fixes the view to properly pull data from:
-- 1. breeds table (has avg_height_cm, avg_male_weight_kg, avg_female_weight_kg)
-- 2. breeds_comprehensive_content (has new min/max columns and other content)
-- 3. breeds_published/breeds_details (existing structure)
--
-- PREREQUISITE: Run add_breed_slug_to_breeds_table.sql first!
-- ============================================

-- First, let's verify the data exists in breeds table
DO $$
DECLARE
    breed_count INTEGER;
    with_height INTEGER;
    with_weight INTEGER;
BEGIN
    SELECT COUNT(*) INTO breed_count FROM breeds;
    SELECT COUNT(*) INTO with_height FROM breeds WHERE avg_height_cm IS NOT NULL;
    SELECT COUNT(*) INTO with_weight FROM breeds WHERE avg_male_weight_kg IS NOT NULL;

    RAISE NOTICE 'Breeds table status:';
    RAISE NOTICE '  Total breeds: %', breed_count;
    RAISE NOTICE '  With height data: % (%.1f%%)', with_height, (with_height::NUMERIC / breed_count * 100);
    RAISE NOTICE '  With weight data: % (%.1f%%)', with_weight, (with_weight::NUMERIC / breed_count * 100);
END $$;

-- Drop the existing view
DROP VIEW IF EXISTS breeds_unified_api CASCADE;
DROP VIEW IF EXISTS breeds_api_statistics CASCADE;

-- Create the improved unified view that aggregates from ALL tables
CREATE VIEW breeds_unified_api AS
SELECT
    -- ===== CORE IDENTIFICATION =====
    bp.id,
    bp.breed_slug,
    bp.display_name,
    bp.aliases,

    -- ===== PHYSICAL CHARACTERISTICS =====
    -- Use COALESCE to prioritize data from different sources
    bp.size_category,

    -- Weight: First try breeds_comprehensive_content min/max, then breeds table averages, then breeds_published
    COALESCE(bcc.weight_min_kg, bp.adult_weight_min_kg) AS adult_weight_min_kg,
    COALESCE(bcc.weight_max_kg, bp.adult_weight_max_kg) AS adult_weight_max_kg,
    COALESCE(
        -- First try average from breeds table
        CASE
            WHEN b.avg_male_weight_kg IS NOT NULL AND b.avg_female_weight_kg IS NOT NULL
            THEN (b.avg_male_weight_kg + b.avg_female_weight_kg) / 2
            WHEN b.avg_male_weight_kg IS NOT NULL THEN b.avg_male_weight_kg
            WHEN b.avg_female_weight_kg IS NOT NULL THEN b.avg_female_weight_kg
            ELSE NULL
        END,
        -- Then fall back to breeds_published
        bp.adult_weight_avg_kg
    ) AS adult_weight_avg_kg,

    -- Height: First try breeds_comprehensive_content min/max, then breeds table average, then breeds_published
    COALESCE(bcc.height_min_cm, bp.height_min_cm) AS height_min_cm,
    COALESCE(bcc.height_max_cm, bp.height_max_cm) AS height_max_cm,
    COALESCE(b.avg_height_cm,
        -- Calculate average from min/max if available
        CASE
            WHEN bcc.height_min_cm IS NOT NULL AND bcc.height_max_cm IS NOT NULL
            THEN (bcc.height_min_cm + bcc.height_max_cm) / 2
            WHEN bp.height_min_cm IS NOT NULL AND bp.height_max_cm IS NOT NULL
            THEN (bp.height_min_cm + bp.height_max_cm) / 2
            ELSE NULL
        END
    ) AS avg_height_cm,

    -- Gender-specific weights from breeds table
    b.avg_male_weight_kg,
    b.avg_female_weight_kg,

    -- Lifespan: Use comprehensive content first, then published
    COALESCE(bcc.lifespan_min_years, bp.lifespan_min_years) AS lifespan_min_years,
    COALESCE(bcc.lifespan_max_years, bp.lifespan_max_years) AS lifespan_max_years,
    COALESCE(bcc.lifespan_avg_years, bp.lifespan_avg_years) AS lifespan_avg_years,

    -- ===== LIFE STAGES =====
    bp.growth_end_months,
    bp.senior_start_months,

    -- ===== BEHAVIORAL TRAITS =====
    -- Prefer comprehensive content for enriched behavioral data
    bp.energy,
    bp.trainability,
    bp.coat_length,  -- Use bp.coat_length as it's already in the right format
    bp.shedding,  -- shedding columns are different types, use bp.shedding
    bp.bark_level,  -- barking_tendency and bark_level are different types
    bp.friendliness_to_dogs,
    bp.friendliness_to_humans,

    -- Additional behavioral traits from comprehensive content
    bcc.coat_texture,
    bcc.drooling_tendency,
    bcc.energy_level_numeric,
    bcc.barking_tendency,  -- Keep this separate from bark_level as they're different types
    bcc.shedding AS shedding_text,  -- Keep bcc.shedding separate with alias since types differ

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

    -- Activity from breeds table
    b.recommended_daily_exercise_min,
    b.activity_level_profile,

    -- ===== HEALTH INFORMATION =====
    bcc.health_issues,

    -- Nutrition from breeds table
    b.nutrition,
    b.weight_gain_risk_score,
    b.climate_tolerance,

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

    -- ===== CARE PROFILE FROM BREEDS TABLE =====
    b.care_profile,

    -- ===== DATA QUALITY & METADATA =====
    bp.data_quality_grade,
    bp.conflict_flags,
    b.qa_status AS breeds_qa_status,
    b.profile_version,

    -- ===== PROVENANCE TRACKING =====
    bp.size_from,
    bp.weight_from,
    bp.height_from,
    bp.lifespan_from,
    bp.age_bounds_from,
    bp.override_reason,
    b.primary_sources AS breeds_primary_sources,

    -- ===== CONTENT SOURCES =====
    bcc.wikipedia_url,
    bcc.scraped_at,

    -- ===== TIMESTAMPS =====
    bp.created_at,
    GREATEST(
        bp.updated_at,
        COALESCE(bcc.updated_at, bp.updated_at),
        COALESCE(b.last_generated_at, bp.updated_at)
    ) AS updated_at,
    bcc.updated_at as content_updated_at,
    b.last_generated_at as breeds_updated_at,

    -- ===== COMPUTED FIELDS =====
    -- Enhanced content completeness score (0-100)
    ROUND(
        (
            -- Physical characteristics (30 points)
            CASE WHEN bp.size_category IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN COALESCE(b.avg_height_cm, bcc.height_min_cm, bp.height_min_cm) IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN COALESCE(b.avg_male_weight_kg, b.avg_female_weight_kg, bcc.weight_min_kg, bp.adult_weight_avg_kg) IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN COALESCE(bcc.lifespan_min_years, bp.lifespan_min_years) IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN bp.energy IS NOT NULL AND bp.energy != 'moderate' THEN 5 ELSE 0 END +
            CASE WHEN COALESCE(bcc.coat_length, bp.coat_length) IS NOT NULL THEN 5 ELSE 0 END +

            -- Personality & behavior (20 points)
            CASE WHEN bcc.personality_description IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bcc.temperament IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN bcc.personality_traits IS NOT NULL THEN 5 ELSE 0 END +

            -- Care requirements (30 points)
            CASE WHEN bcc.general_care IS NOT NULL THEN 10 ELSE 0 END +
            CASE WHEN bcc.grooming_needs IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN bcc.exercise_needs_detail IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN COALESCE(b.nutrition, bcc.diet_requirements) IS NOT NULL THEN 5 ELSE 0 END +
            CASE WHEN bcc.training_tips IS NOT NULL THEN 5 ELSE 0 END +

            -- Health & wellness (10 points)
            CASE WHEN bcc.health_issues IS NOT NULL THEN 10 ELSE 0 END +

            -- Enrichment content (10 points)
            CASE WHEN array_length(bcc.fun_facts, 1) > 0 THEN 5 ELSE 0 END +
            CASE WHEN array_length(bcc.working_roles, 1) > 0 THEN 5 ELSE 0 END
        )
    , 0) AS content_completeness_score,

    -- Has rich content flag (enhanced to check breeds table data too)
    CASE
        WHEN (bcc.personality_description IS NOT NULL OR b.care_profile IS NOT NULL)
            AND (bcc.general_care IS NOT NULL OR b.nutrition IS NOT NULL)
            AND (b.avg_height_cm IS NOT NULL OR bcc.height_min_cm IS NOT NULL)
            AND (b.avg_male_weight_kg IS NOT NULL OR bcc.weight_min_kg IS NOT NULL)
            AND (array_length(bcc.fun_facts, 1) > 0 OR array_length(bcc.working_roles, 1) > 0)
        THEN true
        ELSE false
    END AS has_rich_content,

    -- Has physical data flag (new)
    CASE
        WHEN (b.avg_height_cm IS NOT NULL OR bcc.height_min_cm IS NOT NULL OR bp.height_min_cm IS NOT NULL)
            AND (b.avg_male_weight_kg IS NOT NULL OR b.avg_female_weight_kg IS NOT NULL OR bcc.weight_min_kg IS NOT NULL OR bp.adult_weight_avg_kg IS NOT NULL)
        THEN true
        ELSE false
    END AS has_physical_data,

    -- Care content word count (combined from multiple sources)
    CASE
        WHEN bcc.general_care IS NOT NULL OR b.care_profile IS NOT NULL
        THEN
            COALESCE(array_length(string_to_array(bcc.general_care, ' '), 1), 0) +
            COALESCE(array_length(string_to_array(b.care_profile, ' '), 1), 0)
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
LEFT JOIN breeds b
    -- Now we can use the simple breed_slug join!
    ON bp.breed_slug = b.breed_slug
WHERE
    -- Only include breeds with good data quality
    bp.data_quality_grade IN ('A+', 'A', 'B')
ORDER BY bp.display_name;

-- Recreate the statistics view
CREATE OR REPLACE VIEW breeds_api_statistics AS
SELECT
    COUNT(*) as total_breeds,
    COUNT(CASE WHEN has_rich_content THEN 1 END) as breeds_with_rich_content,
    COUNT(CASE WHEN has_physical_data THEN 1 END) as breeds_with_physical_data,
    COUNT(CASE WHEN content_completeness_score >= 80 THEN 1 END) as high_quality_breeds,
    COUNT(CASE WHEN content_completeness_score >= 50 AND content_completeness_score < 80 THEN 1 END) as medium_quality_breeds,
    COUNT(CASE WHEN content_completeness_score < 50 THEN 1 END) as low_quality_breeds,
    ROUND(AVG(content_completeness_score), 1) as avg_completeness_score,
    COUNT(CASE WHEN personality_description IS NOT NULL THEN 1 END) as with_personality,
    COUNT(CASE WHEN general_care IS NOT NULL OR care_profile IS NOT NULL THEN 1 END) as with_care_content,
    COUNT(CASE WHEN array_length(fun_facts, 1) > 0 THEN 1 END) as with_fun_facts,
    COUNT(CASE WHEN health_issues IS NOT NULL THEN 1 END) as with_health_info,
    COUNT(CASE WHEN avg_height_cm IS NOT NULL THEN 1 END) as with_height_data,
    COUNT(CASE WHEN avg_male_weight_kg IS NOT NULL OR avg_female_weight_kg IS NOT NULL THEN 1 END) as with_weight_data,
    COUNT(CASE WHEN nutrition IS NOT NULL THEN 1 END) as with_nutrition_data
FROM breeds_unified_api;

-- Grant permissions
GRANT SELECT ON breeds_unified_api TO authenticated;
GRANT SELECT ON breeds_unified_api TO anon;
GRANT SELECT ON breeds_unified_api TO service_role;
GRANT SELECT ON breeds_api_statistics TO authenticated;
GRANT SELECT ON breeds_api_statistics TO anon;

-- Create indexes on the breeds table for better join performance
DO $$
BEGIN
    -- Create index on breeds.breed_slug for efficient joining
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_breeds_breed_slug') THEN
        CREATE INDEX idx_breeds_breed_slug ON breeds(breed_slug);
        RAISE NOTICE 'Created index on breeds.breed_slug';
    END IF;
END $$;

-- Verification: Check the improvement
DO $$
DECLARE
    total_breeds INTEGER;
    with_height INTEGER;
    with_weight INTEGER;
    with_lifespan INTEGER;
    avg_completeness NUMERIC;
BEGIN
    SELECT
        COUNT(*),
        COUNT(CASE WHEN avg_height_cm IS NOT NULL THEN 1 END),
        COUNT(CASE WHEN avg_male_weight_kg IS NOT NULL OR avg_female_weight_kg IS NOT NULL THEN 1 END),
        COUNT(CASE WHEN lifespan_min_years IS NOT NULL THEN 1 END),
        ROUND(AVG(content_completeness_score), 1)
    INTO total_breeds, with_height, with_weight, with_lifespan, avg_completeness
    FROM breeds_unified_api;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'VIEW AGGREGATION FIX COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total breeds in view: %', total_breeds;
    RAISE NOTICE 'Breeds with height data: % (%.1f%%)', with_height, (with_height::NUMERIC / total_breeds * 100);
    RAISE NOTICE 'Breeds with weight data: % (%.1f%%)', with_weight, (with_weight::NUMERIC / total_breeds * 100);
    RAISE NOTICE 'Breeds with lifespan data: % (%.1f%%)', with_lifespan, (with_lifespan::NUMERIC / total_breeds * 100);
    RAISE NOTICE 'Average completeness score: %', avg_completeness;
    RAISE NOTICE '';
    RAISE NOTICE 'The view now properly aggregates data from:';
    RAISE NOTICE '  1. breeds table (height, weight, nutrition, care)';
    RAISE NOTICE '  2. breeds_comprehensive_content (enriched content)';
    RAISE NOTICE '  3. breeds_published (base breed data)';
END $$;

-- Show sample breeds with improved data
SELECT
    breed_slug,
    display_name,
    avg_height_cm,
    avg_male_weight_kg,
    avg_female_weight_kg,
    content_completeness_score,
    has_physical_data
FROM breeds_unified_api
WHERE avg_height_cm IS NOT NULL
LIMIT 5;