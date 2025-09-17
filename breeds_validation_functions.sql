-- ============================================
-- BREEDS VALIDATION FUNCTIONS AND TRIGGERS
-- ============================================

-- 1. Function to validate breed weight consistency with size category
CREATE OR REPLACE FUNCTION validate_breed_weight_size()
RETURNS TABLE (
    breed_slug TEXT,
    display_name TEXT,
    size_category TEXT,
    weight_avg NUMERIC,
    issue TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        bp.breed_slug,
        bp.display_name,
        bp.size_category,
        bp.adult_weight_avg_kg,
        CASE
            WHEN bp.size_category = 'xs' AND bp.adult_weight_avg_kg > 7 THEN 'XS breed too heavy (>7kg)'
            WHEN bp.size_category = 's' AND bp.adult_weight_avg_kg > 15 THEN 'S breed too heavy (>15kg)'
            WHEN bp.size_category = 's' AND bp.adult_weight_avg_kg < 5 THEN 'S breed too light (<5kg)'
            WHEN bp.size_category = 'm' AND bp.adult_weight_avg_kg > 30 THEN 'M breed too heavy (>30kg)'
            WHEN bp.size_category = 'm' AND bp.adult_weight_avg_kg < 10 THEN 'M breed too light (<10kg)'
            WHEN bp.size_category = 'l' AND bp.adult_weight_avg_kg > 50 THEN 'L breed too heavy (>50kg)'
            WHEN bp.size_category = 'l' AND bp.adult_weight_avg_kg < 25 THEN 'L breed too light (<25kg)'
            WHEN bp.size_category = 'xl' AND bp.adult_weight_avg_kg < 40 THEN 'XL breed too light (<40kg)'
            ELSE NULL
        END AS issue
    FROM breeds_published bp
    WHERE bp.adult_weight_avg_kg IS NOT NULL
    AND CASE
        WHEN bp.size_category = 'xs' AND bp.adult_weight_avg_kg > 7 THEN true
        WHEN bp.size_category = 's' AND (bp.adult_weight_avg_kg > 15 OR bp.adult_weight_avg_kg < 5) THEN true
        WHEN bp.size_category = 'm' AND (bp.adult_weight_avg_kg > 30 OR bp.adult_weight_avg_kg < 10) THEN true
        WHEN bp.size_category = 'l' AND (bp.adult_weight_avg_kg > 50 OR bp.adult_weight_avg_kg < 25) THEN true
        WHEN bp.size_category = 'xl' AND bp.adult_weight_avg_kg < 40 THEN true
        ELSE false
    END;
END;
$$ LANGUAGE plpgsql;

-- 2. Function to check data quality and assign grade
CREATE OR REPLACE FUNCTION calculate_breed_quality_grade(breed_slug_input TEXT)
RETURNS TEXT AS $$
DECLARE
    score INTEGER := 0;
    total_checks INTEGER := 0;
    breed_record RECORD;
BEGIN
    SELECT * INTO breed_record
    FROM breeds_published
    WHERE breed_slug = breed_slug_input;

    IF NOT FOUND THEN
        RETURN 'N/A';
    END IF;

    -- Check weight data (20 points)
    total_checks := total_checks + 20;
    IF breed_record.adult_weight_min_kg IS NOT NULL AND
       breed_record.adult_weight_max_kg IS NOT NULL AND
       breed_record.adult_weight_avg_kg IS NOT NULL THEN
        score := score + 20;
    ELSIF breed_record.adult_weight_avg_kg IS NOT NULL THEN
        score := score + 10;
    END IF;

    -- Check height data (15 points)
    total_checks := total_checks + 15;
    IF breed_record.height_min_cm IS NOT NULL AND
       breed_record.height_max_cm IS NOT NULL THEN
        score := score + 15;
    ELSIF breed_record.height_min_cm IS NOT NULL OR
          breed_record.height_max_cm IS NOT NULL THEN
        score := score + 8;
    END IF;

    -- Check lifespan data (15 points)
    total_checks := total_checks + 15;
    IF breed_record.lifespan_min_years IS NOT NULL AND
       breed_record.lifespan_max_years IS NOT NULL AND
       breed_record.lifespan_avg_years IS NOT NULL THEN
        score := score + 15;
    ELSIF breed_record.lifespan_avg_years IS NOT NULL THEN
        score := score + 8;
    END IF;

    -- Check size category (20 points)
    total_checks := total_checks + 20;
    IF breed_record.size_category IS NOT NULL THEN
        score := score + 20;
    END IF;

    -- Check age boundaries (15 points)
    total_checks := total_checks + 15;
    IF breed_record.growth_end_months IS NOT NULL AND
       breed_record.senior_start_months IS NOT NULL THEN
        score := score + 15;
    END IF;

    -- Check energy level (15 points)
    total_checks := total_checks + 15;
    IF breed_record.energy IS NOT NULL AND
       breed_record.energy != 'moderate' THEN
        score := score + 15;
    ELSIF breed_record.energy IS NOT NULL THEN
        score := score + 5;
    END IF;

    -- Calculate percentage and assign grade
    DECLARE
        percentage NUMERIC := (score::NUMERIC / total_checks) * 100;
    BEGIN
        IF percentage >= 95 THEN RETURN 'A+';
        ELSIF percentage >= 90 THEN RETURN 'A';
        ELSIF percentage >= 85 THEN RETURN 'A-';
        ELSIF percentage >= 80 THEN RETURN 'B+';
        ELSIF percentage >= 75 THEN RETURN 'B';
        ELSIF percentage >= 70 THEN RETURN 'B-';
        ELSIF percentage >= 65 THEN RETURN 'C+';
        ELSIF percentage >= 60 THEN RETURN 'C';
        ELSIF percentage >= 55 THEN RETURN 'C-';
        ELSIF percentage >= 50 THEN RETURN 'D';
        ELSE RETURN 'F';
        END IF;
    END;
END;
$$ LANGUAGE plpgsql;

-- 3. Function to update all quality grades
CREATE OR REPLACE FUNCTION update_all_breed_quality_grades()
RETURNS void AS $$
BEGIN
    UPDATE breeds_published
    SET data_quality_grade = calculate_breed_quality_grade(breed_slug);
END;
$$ LANGUAGE plpgsql;

-- 4. Function to apply enrichment data to breeds_published
CREATE OR REPLACE FUNCTION apply_enrichment_to_breeds()
RETURNS void AS $$
BEGIN
    -- Update weight data from enrichment
    UPDATE breeds_published bp
    SET
        adult_weight_min_kg = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'weight_min_kg'
             AND source = 'wikipedia'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.adult_weight_min_kg
        ),
        adult_weight_max_kg = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'weight_max_kg'
             AND source = 'wikipedia'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.adult_weight_max_kg
        ),
        adult_weight_avg_kg = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'weight_avg_kg'
             AND source = 'wikipedia'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.adult_weight_avg_kg
        ),
        weight_from = CASE
            WHEN EXISTS (SELECT 1 FROM breeds_enrichment
                        WHERE breed_slug = bp.breed_slug
                        AND field_name LIKE 'weight%'
                        AND source = 'wikipedia')
            THEN 'wikipedia'
            ELSE bp.weight_from
        END,
        updated_at = NOW()
    WHERE EXISTS (
        SELECT 1 FROM breeds_enrichment
        WHERE breed_slug = bp.breed_slug
        AND field_name LIKE 'weight%'
    );

    -- Update height data from enrichment
    UPDATE breeds_published bp
    SET
        height_min_cm = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'height_min_cm'
             AND source = 'wikipedia'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.height_min_cm
        ),
        height_max_cm = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'height_max_cm'
             AND source = 'wikipedia'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.height_max_cm
        ),
        height_from = CASE
            WHEN EXISTS (SELECT 1 FROM breeds_enrichment
                        WHERE breed_slug = bp.breed_slug
                        AND field_name LIKE 'height%'
                        AND source = 'wikipedia')
            THEN 'wikipedia'
            ELSE bp.height_from
        END,
        updated_at = NOW()
    WHERE EXISTS (
        SELECT 1 FROM breeds_enrichment
        WHERE breed_slug = bp.breed_slug
        AND field_name LIKE 'height%'
    );

    -- Update lifespan data from enrichment
    UPDATE breeds_published bp
    SET
        lifespan_min_years = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'lifespan_min_years'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.lifespan_min_years
        ),
        lifespan_max_years = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'lifespan_max_years'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.lifespan_max_years
        ),
        lifespan_avg_years = COALESCE(
            (SELECT field_numeric FROM breeds_enrichment
             WHERE breed_slug = bp.breed_slug
             AND field_name = 'lifespan_avg_years'
             ORDER BY confidence_score DESC, fetched_at DESC
             LIMIT 1),
            bp.lifespan_avg_years
        ),
        lifespan_from = CASE
            WHEN EXISTS (SELECT 1 FROM breeds_enrichment
                        WHERE breed_slug = bp.breed_slug
                        AND field_name LIKE 'lifespan%')
            THEN 'enrichment'
            ELSE bp.lifespan_from
        END,
        updated_at = NOW()
    WHERE EXISTS (
        SELECT 1 FROM breeds_enrichment
        WHERE breed_slug = bp.breed_slug
        AND field_name LIKE 'lifespan%'
    );
END;
$$ LANGUAGE plpgsql;

-- 5. Create summary report view
CREATE OR REPLACE VIEW breed_quality_summary AS
SELECT
    data_quality_grade,
    COUNT(*) as breed_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM breeds_published
GROUP BY data_quality_grade
ORDER BY
    CASE data_quality_grade
        WHEN 'A+' THEN 1
        WHEN 'A' THEN 2
        WHEN 'A-' THEN 3
        WHEN 'B+' THEN 4
        WHEN 'B' THEN 5
        WHEN 'B-' THEN 6
        WHEN 'C+' THEN 7
        WHEN 'C' THEN 8
        WHEN 'C-' THEN 9
        WHEN 'D' THEN 10
        WHEN 'F' THEN 11
        ELSE 12
    END;

-- 6. Create missing data summary view
CREATE OR REPLACE VIEW breed_missing_data_summary AS
SELECT
    'Weight Data' as field_category,
    COUNT(*) FILTER (WHERE adult_weight_avg_kg IS NULL) as missing_count,
    COUNT(*) as total_count,
    ROUND(100.0 - (COUNT(*) FILTER (WHERE adult_weight_avg_kg IS NULL) * 100.0 / COUNT(*)), 2) as coverage_percentage
FROM breeds_published
UNION ALL
SELECT
    'Height Data' as field_category,
    COUNT(*) FILTER (WHERE height_min_cm IS NULL AND height_max_cm IS NULL) as missing_count,
    COUNT(*) as total_count,
    ROUND(100.0 - (COUNT(*) FILTER (WHERE height_min_cm IS NULL AND height_max_cm IS NULL) * 100.0 / COUNT(*)), 2) as coverage_percentage
FROM breeds_published
UNION ALL
SELECT
    'Lifespan Data' as field_category,
    COUNT(*) FILTER (WHERE lifespan_avg_years IS NULL) as missing_count,
    COUNT(*) as total_count,
    ROUND(100.0 - (COUNT(*) FILTER (WHERE lifespan_avg_years IS NULL) * 100.0 / COUNT(*)), 2) as coverage_percentage
FROM breeds_published
UNION ALL
SELECT
    'Non-default Energy' as field_category,
    COUNT(*) FILTER (WHERE energy = 'moderate' OR energy IS NULL) as missing_count,
    COUNT(*) as total_count,
    ROUND(100.0 - (COUNT(*) FILTER (WHERE energy = 'moderate' OR energy IS NULL) * 100.0 / COUNT(*)), 2) as coverage_percentage
FROM breeds_published;

-- Grant permissions
GRANT EXECUTE ON FUNCTION validate_breed_weight_size() TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_breed_quality_grade(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION update_all_breed_quality_grades() TO authenticated;
GRANT EXECUTE ON FUNCTION apply_enrichment_to_breeds() TO authenticated;
GRANT SELECT ON breed_quality_summary TO authenticated;
GRANT SELECT ON breed_missing_data_summary TO authenticated;