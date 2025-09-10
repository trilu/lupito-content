-- Publish Reconciled Breeds View with Grade A+ Data
-- This creates the production view with proper precedence and provenance

-- 1. Rename current breeds_published to breeds_published_prev for rollback
ALTER VIEW IF EXISTS breeds_published RENAME TO breeds_published_prev;

-- 2. Create the reconciled view with proper precedence
CREATE OR REPLACE VIEW breeds_published AS
SELECT 
    bd.id,
    bd.breed_slug,
    bd.display_name,
    bd.aliases,
    
    -- Size category with precedence: overrides > calculated > legacy
    COALESCE(
        bo.size_category,
        bd.size_category
    ) as size_category,
    
    -- Growth/Senior months with precedence
    COALESCE(
        bo.growth_end_months,
        bd.growth_end_months
    ) as growth_end_months,
    
    COALESCE(
        bo.senior_start_months,
        bd.senior_start_months
    ) as senior_start_months,
    
    -- Weight data with precedence
    COALESCE(
        bo.adult_weight_min_kg,
        bd.weight_kg_min
    ) as adult_weight_min_kg,
    
    COALESCE(
        bo.adult_weight_max_kg,
        bd.weight_kg_max
    ) as adult_weight_max_kg,
    
    COALESCE(
        bo.adult_weight_avg_kg,
        bd.adult_weight_avg_kg
    ) as adult_weight_avg_kg,
    
    -- Height data with precedence
    COALESCE(
        bo.height_min_cm,
        bd.height_cm_min
    ) as height_min_cm,
    
    COALESCE(
        bo.height_max_cm,
        bd.height_cm_max
    ) as height_max_cm,
    
    -- Lifespan data with precedence
    COALESCE(
        bo.lifespan_min_years,
        bd.lifespan_years_min
    ) as lifespan_min_years,
    
    COALESCE(
        bo.lifespan_max_years,
        bd.lifespan_years_max
    ) as lifespan_max_years,
    
    COALESCE(
        bo.lifespan_avg_years,
        bd.lifespan_avg_years
    ) as lifespan_avg_years,
    
    -- Other fields
    bd.energy,
    bd.trainability,
    bd.coat_length,
    bd.shedding,
    bd.bark_level,
    bd.origin,
    bd.friendliness_to_dogs,
    bd.friendliness_to_humans,
    bd.comprehensive_content,
    
    -- Provenance fields
    CASE 
        WHEN bo.size_category IS NOT NULL THEN 'override'
        ELSE bd.size_from
    END as size_from,
    
    CASE 
        WHEN bo.adult_weight_avg_kg IS NOT NULL THEN 'override'
        ELSE bd.weight_from
    END as weight_from,
    
    CASE 
        WHEN bo.height_min_cm IS NOT NULL THEN 'override'
        ELSE bd.height_from
    END as height_from,
    
    CASE 
        WHEN bo.lifespan_avg_years IS NOT NULL THEN 'override'
        ELSE bd.lifespan_from
    END as lifespan_from,
    
    CASE 
        WHEN bo.growth_end_months IS NOT NULL THEN 'override'
        ELSE bd.age_bounds_from
    END as age_bounds_from,
    
    -- Conflict flags
    bd.conflict_flags,
    
    -- Override reason if applicable
    bo.override_reason,
    
    -- Timestamps
    bd.created_at,
    GREATEST(bd.updated_at, bo.updated_at) as updated_at,
    
    -- Data quality score (calculated)
    CASE 
        WHEN COALESCE(bo.size_category, bd.size_category) IS NOT NULL 
         AND COALESCE(bo.growth_end_months, bd.growth_end_months) IS NOT NULL
         AND COALESCE(bo.senior_start_months, bd.senior_start_months) IS NOT NULL
         AND COALESCE(bo.adult_weight_avg_kg, bd.adult_weight_avg_kg) IS NOT NULL
        THEN 'A+'
        WHEN COALESCE(bo.adult_weight_avg_kg, bd.adult_weight_avg_kg) IS NOT NULL
        THEN 'A'
        WHEN COALESCE(bo.size_category, bd.size_category) IS NOT NULL
        THEN 'B'
        ELSE 'C'
    END as data_quality_grade

FROM breeds_details bd
LEFT JOIN breeds_overrides bo ON bd.breed_slug = bo.breed_slug
ORDER BY bd.display_name;

-- 3. Create indexes for performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_breeds_published_slug ON breeds_details(breed_slug);
CREATE INDEX IF NOT EXISTS idx_breeds_published_size ON breeds_details(size_category);
CREATE INDEX IF NOT EXISTS idx_breeds_published_quality ON breeds_details(size_category, growth_end_months, adult_weight_avg_kg);

-- 4. Add constraint to ensure breed_slug uniqueness
ALTER TABLE breeds_details ADD CONSTRAINT unique_breed_slug UNIQUE (breed_slug) ON CONFLICT DO NOTHING;

-- 5. Grant appropriate permissions
GRANT SELECT ON breeds_published TO authenticated;
GRANT SELECT ON breeds_published TO anon;

-- 6. Create a function to get breed by slug (optimized)
CREATE OR REPLACE FUNCTION get_breed_published(p_breed_slug VARCHAR)
RETURNS TABLE (
    breed_slug VARCHAR,
    display_name VARCHAR,
    size_category VARCHAR,
    adult_weight_avg_kg DECIMAL,
    growth_end_months INTEGER,
    senior_start_months INTEGER,
    data_quality_grade VARCHAR
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bp.breed_slug,
        bp.display_name,
        bp.size_category,
        bp.adult_weight_avg_kg,
        bp.growth_end_months,
        bp.senior_start_months,
        bp.data_quality_grade
    FROM breeds_published bp
    WHERE bp.breed_slug = p_breed_slug
    LIMIT 1;
END;
$$;

-- 7. Create view for data quality monitoring
CREATE OR REPLACE VIEW breeds_quality_metrics AS
SELECT 
    COUNT(*) as total_breeds,
    COUNT(CASE WHEN size_category IS NOT NULL THEN 1 END) as with_size,
    COUNT(CASE WHEN adult_weight_avg_kg IS NOT NULL THEN 1 END) as with_weight,
    COUNT(CASE WHEN growth_end_months IS NOT NULL THEN 1 END) as with_growth,
    COUNT(CASE WHEN data_quality_grade = 'A+' THEN 1 END) as grade_a_plus,
    COUNT(CASE WHEN data_quality_grade = 'A' THEN 1 END) as grade_a,
    COUNT(CASE WHEN data_quality_grade = 'B' THEN 1 END) as grade_b,
    COUNT(CASE WHEN data_quality_grade = 'C' THEN 1 END) as grade_c,
    ROUND(COUNT(CASE WHEN size_category IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as size_coverage_pct,
    ROUND(COUNT(CASE WHEN adult_weight_avg_kg IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as weight_coverage_pct,
    ROUND(COUNT(CASE WHEN growth_end_months IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as growth_coverage_pct
FROM breeds_published;

-- Verify the view was created successfully
SELECT 
    'View created successfully' as status,
    COUNT(*) as total_breeds,
    ROUND(AVG(CASE WHEN size_category IS NOT NULL THEN 100.0 ELSE 0 END), 1) as size_coverage,
    ROUND(AVG(CASE WHEN adult_weight_avg_kg IS NOT NULL THEN 100.0 ELSE 0 END), 1) as weight_coverage,
    ROUND(AVG(CASE WHEN growth_end_months IS NOT NULL THEN 100.0 ELSE 0 END), 1) as growth_coverage
FROM breeds_published;