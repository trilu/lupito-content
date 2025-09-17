-- ============================================
-- APPLY OVERRIDES TO UNDERLYING BREEDS_DETAILS TABLE
-- ============================================

-- First, let's check what the breeds_published view is based on
-- The view likely joins breeds_details with other tables

-- Apply size_category overrides to breeds_details
UPDATE breeds_details bd
SET
    size_category = COALESCE(bo.size_category, bd.size_category),
    size_from = CASE WHEN bo.size_category IS NOT NULL THEN 'override' ELSE bd.size_from END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bd.breed_slug = bo.breed_slug
AND bo.size_category IS NOT NULL;

-- Apply weight overrides to breeds_details
UPDATE breeds_details bd
SET
    weight_kg_min = COALESCE(bo.adult_weight_min_kg, bd.weight_kg_min),
    weight_kg_max = COALESCE(bo.adult_weight_max_kg, bd.weight_kg_max),
    adult_weight_avg_kg = COALESCE(bo.adult_weight_avg_kg, bd.adult_weight_avg_kg),
    weight_from = CASE
        WHEN bo.adult_weight_min_kg IS NOT NULL OR bo.adult_weight_max_kg IS NOT NULL OR bo.adult_weight_avg_kg IS NOT NULL
        THEN 'override'
        ELSE bd.weight_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bd.breed_slug = bo.breed_slug
AND (bo.adult_weight_min_kg IS NOT NULL OR bo.adult_weight_max_kg IS NOT NULL OR bo.adult_weight_avg_kg IS NOT NULL);

-- Apply height overrides to breeds_details
UPDATE breeds_details bd
SET
    height_cm_min = COALESCE(bo.height_min_cm, bd.height_cm_min),
    height_cm_max = COALESCE(bo.height_max_cm, bd.height_cm_max),
    height_from = CASE
        WHEN bo.height_min_cm IS NOT NULL OR bo.height_max_cm IS NOT NULL
        THEN 'override'
        ELSE bd.height_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bd.breed_slug = bo.breed_slug
AND (bo.height_min_cm IS NOT NULL OR bo.height_max_cm IS NOT NULL);

-- Apply lifespan overrides to breeds_details
UPDATE breeds_details bd
SET
    lifespan_years_min = COALESCE(bo.lifespan_min_years, bd.lifespan_years_min),
    lifespan_years_max = COALESCE(bo.lifespan_max_years, bd.lifespan_years_max),
    lifespan_avg_years = COALESCE(bo.lifespan_avg_years, bd.lifespan_avg_years),
    lifespan_from = CASE
        WHEN bo.lifespan_min_years IS NOT NULL OR bo.lifespan_max_years IS NOT NULL OR bo.lifespan_avg_years IS NOT NULL
        THEN 'override'
        ELSE bd.lifespan_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bd.breed_slug = bo.breed_slug
AND (bo.lifespan_min_years IS NOT NULL OR bo.lifespan_max_years IS NOT NULL OR bo.lifespan_avg_years IS NOT NULL);

-- Apply age boundary overrides to breeds_details
UPDATE breeds_details bd
SET
    growth_end_months = COALESCE(bo.growth_end_months, bd.growth_end_months),
    senior_start_months = COALESCE(bo.senior_start_months, bd.senior_start_months),
    age_bounds_from = CASE
        WHEN bo.growth_end_months IS NOT NULL OR bo.senior_start_months IS NOT NULL
        THEN 'override'
        ELSE bd.age_bounds_from
    END,
    updated_at = NOW()
FROM breeds_overrides bo
WHERE bd.breed_slug = bo.breed_slug
AND (bo.growth_end_months IS NOT NULL OR bo.senior_start_months IS NOT NULL);

-- Report on what was updated
WITH override_summary AS (
    SELECT
        COUNT(DISTINCT bo.breed_slug) as total_overrides,
        COUNT(DISTINCT CASE WHEN bo.size_category IS NOT NULL THEN bo.breed_slug END) as size_overrides,
        COUNT(DISTINCT CASE WHEN bo.adult_weight_avg_kg IS NOT NULL THEN bo.breed_slug END) as weight_overrides,
        COUNT(DISTINCT CASE WHEN bo.height_min_cm IS NOT NULL OR bo.height_max_cm IS NOT NULL THEN bo.breed_slug END) as height_overrides,
        COUNT(DISTINCT CASE WHEN bo.lifespan_avg_years IS NOT NULL THEN bo.breed_slug END) as lifespan_overrides
    FROM breeds_overrides bo
)
SELECT
    'Overrides Applied to breeds_details' as status,
    total_overrides as breeds_with_overrides,
    size_overrides,
    weight_overrides,
    height_overrides,
    lifespan_overrides
FROM override_summary;

-- Show which breeds were updated
SELECT
    bd.breed_slug,
    bd.display_name,
    bd.size_category,
    bd.size_from,
    bo.override_reason
FROM breeds_details bd
JOIN breeds_overrides bo ON bd.breed_slug = bo.breed_slug
WHERE bo.size_category IS NOT NULL
ORDER BY bd.breed_slug;