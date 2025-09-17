-- ============================================
-- APPLY EXISTING OVERRIDES TO BREEDS
-- ============================================

-- The breeds_overrides table already exists and contains direct value overrides
-- Let's apply these overrides to the breeds_published table

-- Apply size_category overrides
UPDATE breeds_published bp
SET
    size_category = COALESCE(bo.size_category, bp.size_category),
    size_from = CASE WHEN bo.size_category IS NOT NULL THEN 'override' ELSE bp.size_from END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bp.breed_slug = bo.breed_slug
AND bo.size_category IS NOT NULL;

-- Apply weight overrides
UPDATE breeds_published bp
SET
    adult_weight_min_kg = COALESCE(bo.adult_weight_min_kg, bp.adult_weight_min_kg),
    adult_weight_max_kg = COALESCE(bo.adult_weight_max_kg, bp.adult_weight_max_kg),
    adult_weight_avg_kg = COALESCE(bo.adult_weight_avg_kg, bp.adult_weight_avg_kg),
    weight_from = CASE
        WHEN bo.adult_weight_min_kg IS NOT NULL OR bo.adult_weight_max_kg IS NOT NULL OR bo.adult_weight_avg_kg IS NOT NULL
        THEN 'override'
        ELSE bp.weight_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bp.breed_slug = bo.breed_slug
AND (bo.adult_weight_min_kg IS NOT NULL OR bo.adult_weight_max_kg IS NOT NULL OR bo.adult_weight_avg_kg IS NOT NULL);

-- Apply height overrides
UPDATE breeds_published bp
SET
    height_min_cm = COALESCE(bo.height_min_cm, bp.height_min_cm),
    height_max_cm = COALESCE(bo.height_max_cm, bp.height_max_cm),
    height_from = CASE
        WHEN bo.height_min_cm IS NOT NULL OR bo.height_max_cm IS NOT NULL
        THEN 'override'
        ELSE bp.height_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bp.breed_slug = bo.breed_slug
AND (bo.height_min_cm IS NOT NULL OR bo.height_max_cm IS NOT NULL);

-- Apply lifespan overrides
UPDATE breeds_published bp
SET
    lifespan_min_years = COALESCE(bo.lifespan_min_years, bp.lifespan_min_years),
    lifespan_max_years = COALESCE(bo.lifespan_max_years, bp.lifespan_max_years),
    lifespan_avg_years = COALESCE(bo.lifespan_avg_years, bp.lifespan_avg_years),
    lifespan_from = CASE
        WHEN bo.lifespan_min_years IS NOT NULL OR bo.lifespan_max_years IS NOT NULL OR bo.lifespan_avg_years IS NOT NULL
        THEN 'override'
        ELSE bp.lifespan_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bp.breed_slug = bo.breed_slug
AND (bo.lifespan_min_years IS NOT NULL OR bo.lifespan_max_years IS NOT NULL OR bo.lifespan_avg_years IS NOT NULL);

-- Apply age boundary overrides
UPDATE breeds_published bp
SET
    growth_end_months = COALESCE(bo.growth_end_months, bp.growth_end_months),
    senior_start_months = COALESCE(bo.senior_start_months, bp.senior_start_months),
    age_bounds_from = CASE
        WHEN bo.growth_end_months IS NOT NULL OR bo.senior_start_months IS NOT NULL
        THEN 'override'
        ELSE bp.age_bounds_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bp.breed_slug = bo.breed_slug
AND (bo.growth_end_months IS NOT NULL OR bo.senior_start_months IS NOT NULL);

-- Apply override_reason if it exists
UPDATE breeds_published bp
SET
    override_reason = COALESCE(bo.override_reason, bp.override_reason),
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bp.breed_slug = bo.breed_slug
AND bo.override_reason IS NOT NULL;

-- Report on what was updated
SELECT
    'Overrides Applied' as status,
    COUNT(DISTINCT bo.breed_slug) as breeds_with_overrides,
    COUNT(DISTINCT CASE WHEN bo.size_category IS NOT NULL THEN bo.breed_slug END) as size_overrides,
    COUNT(DISTINCT CASE WHEN bo.adult_weight_avg_kg IS NOT NULL THEN bo.breed_slug END) as weight_overrides,
    COUNT(DISTINCT CASE WHEN bo.height_min_cm IS NOT NULL OR bo.height_max_cm IS NOT NULL THEN bo.breed_slug END) as height_overrides,
    COUNT(DISTINCT CASE WHEN bo.lifespan_avg_years IS NOT NULL THEN bo.breed_slug END) as lifespan_overrides
FROM breeds_overrides bo;