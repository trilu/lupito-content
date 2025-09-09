-- ============================================================================
-- BREEDS CONSOLIDATION PIPELINE - COMPLETE SQL
-- ============================================================================

-- ============================================================================
-- STEP 0: Clean up existing views/tables
-- ============================================================================

DROP VIEW IF EXISTS breeds_published CASCADE;
DROP TABLE IF EXISTS breeds_canonical CASCADE;
DROP VIEW IF EXISTS breeds_union_all CASCADE;
DROP VIEW IF EXISTS breed_raw_compat CASCADE;
DROP VIEW IF EXISTS breeds_compat CASCADE;
DROP VIEW IF EXISTS breeds_details_compat CASCADE;
DROP TABLE IF EXISTS breed_aliases CASCADE;

-- ============================================================================
-- STEP B1: Create Breed Aliases Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS breed_aliases (
    alias TEXT PRIMARY KEY,
    canonical_slug TEXT NOT NULL,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Populate initial aliases based on discovered clusters
INSERT INTO breed_aliases (alias, canonical_slug, source) VALUES
    ('brittany', 'brittany', 'auto'),
    ('Brittany', 'brittany', 'auto'),
    ('bullmastiff', 'bullmastiff', 'auto'),
    ('Bullmastiff', 'bullmastiff', 'auto'),
    ('chihuahua', 'chihuahua', 'auto'),
    ('Chihuahua', 'chihuahua', 'auto'),
    ('dalmatian', 'dalmatian', 'auto'),
    ('Dalmatian', 'dalmatian', 'auto'),
    ('pomeranian', 'pomeranian', 'auto'),
    ('Pomeranian', 'pomeranian', 'auto'),
    ('rottweiler', 'rottweiler', 'auto'),
    ('Rottweiler', 'rottweiler', 'auto'),
    ('beagle', 'beagle', 'auto'),
    ('Beagle', 'beagle', 'auto')
ON CONFLICT (alias) DO NOTHING;

-- ============================================================================
-- STEP B2: Create Compatibility Views
-- ============================================================================

-- 1. breed_raw_compat
CREATE VIEW breed_raw_compat AS
SELECT 
    -- Core identifiers
    breed_slug as breed_id,
    breed_slug as breed_name,
    breed_slug,
    
    -- Size (not available in this table)
    NULL::text as size_category,
    
    -- Age boundaries (not available)
    NULL::integer as growth_end_months,
    NULL::integer as senior_start_months,
    
    -- Activity (not available)
    NULL::text as activity_baseline,
    NULL::numeric as energy_factor_mod,
    
    -- Weight (not available)
    NULL::numeric as ideal_weight_min_kg,
    NULL::numeric as ideal_weight_max_kg,
    
    -- Metadata
    jsonb_build_object(
        'source', 'breed_raw',
        'first_seen_at', first_seen_at,
        'last_seen_at', last_seen_at
    ) as sources,
    COALESCE(last_seen_at, first_seen_at) as updated_at
    
FROM breed_raw
WHERE breed_slug IS NOT NULL;

-- 2. breeds_compat
CREATE VIEW breeds_compat AS
SELECT 
    -- Core identifiers
    LOWER(REPLACE(name_en, ' ', '-')) as breed_id,
    name_en as breed_name,
    LOWER(REPLACE(name_en, ' ', '-')) as breed_slug,
    
    -- Size mapping
    CASE 
        WHEN size_category = 'XS' THEN 'xs'
        WHEN size_category = 'S' THEN 's'
        WHEN size_category = 'M' THEN 'm'
        WHEN size_category = 'L' THEN 'l'
        WHEN size_category = 'XL' THEN 'xl'
        WHEN size_category = 'Giant' THEN 'xl'
        ELSE LOWER(size_category)
    END as size_category,
    
    -- Age boundaries (use defaults based on size if not available)
    CASE 
        WHEN size_category IN ('XS', 'S') THEN 10  -- Small breeds mature faster
        WHEN size_category = 'M' THEN 12
        WHEN size_category IN ('L', 'XL', 'Giant') THEN 15  -- Large breeds mature slower
        ELSE 12  -- Default
    END as growth_end_months,
    
    CASE 
        WHEN size_category IN ('XS', 'S') THEN 108  -- Small breeds: 9 years
        WHEN size_category = 'M' THEN 96  -- Medium: 8 years
        WHEN size_category IN ('L', 'XL', 'Giant') THEN 84  -- Large: 7 years
        ELSE 96  -- Default
    END as senior_start_months,
    
    -- Activity mapping from activity_level_profile
    CASE 
        WHEN activity_level_profile ~* 'very.?high|extremely' THEN 'very_high'
        WHEN activity_level_profile ~* 'high' THEN 'high'
        WHEN activity_level_profile ~* 'low' THEN 'low'
        ELSE 'moderate'
    END as activity_baseline,
    
    -- Energy factor modifier (conservative estimates)
    CASE 
        WHEN activity_level_profile ~* 'very.?high|extremely' THEN 0.10
        WHEN activity_level_profile ~* 'high' THEN 0.05
        WHEN activity_level_profile ~* 'low' THEN -0.05
        ELSE 0.0
    END as energy_factor_mod,
    
    -- Weight ranges
    avg_male_weight_kg - 2 as ideal_weight_min_kg,  -- Approximate range
    avg_male_weight_kg + 2 as ideal_weight_max_kg,
    
    -- Metadata
    jsonb_build_object(
        'source', 'breeds',
        'last_generated_at', last_generated_at,
        'default_age_boundaries', true
    ) as sources,
    COALESCE(last_generated_at, NOW()) as updated_at
    
FROM breeds
WHERE name_en IS NOT NULL;

-- 3. breeds_details_compat (Wikipedia-scraped data)
CREATE VIEW breeds_details_compat AS
SELECT 
    -- Core identifiers
    breed_slug as breed_id,
    display_name as breed_name,
    breed_slug,
    
    -- Size mapping
    CASE 
        WHEN size = 'tiny' THEN 'xs'
        WHEN size = 'small' THEN 's'
        WHEN size = 'medium' THEN 'm'
        WHEN size = 'large' THEN 'l'
        WHEN size = 'giant' THEN 'xl'
        WHEN weight_kg_max <= 7 THEN 'xs'
        WHEN weight_kg_max <= 15 THEN 's'
        WHEN weight_kg_max <= 30 THEN 'm'
        WHEN weight_kg_max <= 50 THEN 'l'
        WHEN weight_kg_max > 50 THEN 'xl'
        ELSE NULL
    END as size_category,
    
    -- Age boundaries based on lifespan data
    CASE 
        WHEN weight_kg_max <= 15 THEN 10  -- Small breeds mature faster
        WHEN weight_kg_max <= 30 THEN 12
        WHEN weight_kg_max > 30 THEN 15   -- Large breeds mature slower
        ELSE 12
    END as growth_end_months,
    
    -- Senior start based on lifespan
    CASE 
        WHEN lifespan_years_max >= 14 THEN 108  -- Long-lived breeds: 9 years
        WHEN lifespan_years_max >= 12 THEN 96   -- Average: 8 years
        WHEN lifespan_years_max >= 10 THEN 84   -- Shorter-lived: 7 years
        ELSE 96
    END as senior_start_months,
    
    -- Activity mapping from energy field (enum values)
    CASE 
        WHEN energy = 'high' THEN 'high'
        WHEN energy = 'low' THEN 'low'
        WHEN energy = 'moderate' THEN 'moderate'
        ELSE 'moderate'
    END as activity_baseline,
    
    -- Energy factor modifier
    CASE 
        WHEN energy = 'high' THEN 0.05
        WHEN energy = 'low' THEN -0.05
        ELSE 0.0
    END as energy_factor_mod,
    
    -- Weight ranges
    weight_kg_min as ideal_weight_min_kg,
    weight_kg_max as ideal_weight_max_kg,
    
    -- Metadata
    jsonb_build_object(
        'source', 'breeds_details',
        'created_at', created_at,
        'has_wikipedia_data', true,
        'energy_score', energy,
        'trainability', trainability,
        'bark_level', bark_level
    ) as sources,
    updated_at
    
FROM breeds_details
WHERE breed_slug IS NOT NULL;


-- ============================================================================
-- STEP B3: Union and Canonical Table
-- ============================================================================

-- Create union view
CREATE VIEW breeds_union_all AS
SELECT * FROM breed_raw_compat
UNION ALL
SELECT * FROM breeds_compat
UNION ALL
SELECT * FROM breeds_details_compat;

-- Create canonical table with deduplication
CREATE TABLE breeds_canonical AS
WITH ranked_breeds AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY breed_slug
            ORDER BY 
                -- Prefer records with more complete data
                CASE WHEN size_category IS NOT NULL THEN 1 ELSE 2 END,
                CASE WHEN ideal_weight_min_kg IS NOT NULL THEN 1 ELSE 2 END,
                CASE WHEN activity_baseline IS NOT NULL THEN 1 ELSE 2 END,
                -- Prefer non-default age boundaries
                CASE WHEN sources->>'default_age_boundaries' = 'true' THEN 2 ELSE 1 END,
                -- Prefer newer data
                updated_at DESC NULLS LAST
        ) as rank
    FROM breeds_union_all
),
aggregated_sources AS (
    SELECT 
        breed_slug,
        jsonb_agg(sources ORDER BY rank) as all_sources
    FROM ranked_breeds
    GROUP BY breed_slug
)
SELECT 
    r.breed_id,
    r.breed_name,
    r.breed_slug,
    r.size_category,
    r.growth_end_months,
    r.senior_start_months,
    r.activity_baseline,
    r.energy_factor_mod,
    r.ideal_weight_min_kg,
    r.ideal_weight_max_kg,
    a.all_sources as sources,
    r.updated_at
FROM ranked_breeds r
JOIN aggregated_sources a ON r.breed_slug = a.breed_slug
WHERE r.rank = 1;

-- Add indexes
CREATE UNIQUE INDEX idx_breeds_canonical_slug ON breeds_canonical(breed_slug);
CREATE INDEX idx_breeds_canonical_size ON breeds_canonical(size_category);
CREATE INDEX idx_breeds_canonical_activity ON breeds_canonical(activity_baseline);

-- ============================================================================
-- STEP B4: Published View for AI/Admin
-- ============================================================================

CREATE VIEW breeds_published AS
SELECT 
    breed_id,
    breed_name,
    breed_slug,
    -- Apply defaults where needed
    COALESCE(size_category, 'm') as size_category,
    COALESCE(growth_end_months, 12) as growth_end_months,
    COALESCE(senior_start_months, 96) as senior_start_months,
    COALESCE(activity_baseline, 'moderate') as activity_baseline,
    COALESCE(energy_factor_mod, 0.0) as energy_factor_mod,
    ideal_weight_min_kg,
    ideal_weight_max_kg,
    sources,
    updated_at
FROM breeds_canonical;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check row counts
SELECT 
    'breed_raw_compat' as view_name, COUNT(*) as row_count 
FROM breed_raw_compat
UNION ALL
SELECT 'breeds_compat', COUNT(*) FROM breeds_compat
UNION ALL
SELECT 'breeds_details_compat', COUNT(*) FROM breeds_details_compat
UNION ALL
SELECT 'breeds_union_all', COUNT(*) FROM breeds_union_all
UNION ALL
SELECT 'breeds_canonical', COUNT(*) FROM breeds_canonical
UNION ALL
SELECT 'breeds_published', COUNT(*) FROM breeds_published
ORDER BY view_name;

-- Check coverage metrics
SELECT 
    COUNT(*) as total_breeds,
    ROUND(100.0 * COUNT(CASE WHEN size_category IS NOT NULL THEN 1 END) / COUNT(*), 1) as size_pct,
    ROUND(100.0 * COUNT(CASE WHEN growth_end_months IS NOT NULL THEN 1 END) / COUNT(*), 1) as growth_pct,
    ROUND(100.0 * COUNT(CASE WHEN senior_start_months IS NOT NULL THEN 1 END) / COUNT(*), 1) as senior_pct,
    ROUND(100.0 * COUNT(CASE WHEN activity_baseline IS NOT NULL THEN 1 END) / COUNT(*), 1) as activity_pct,
    ROUND(100.0 * COUNT(CASE WHEN ideal_weight_min_kg IS NOT NULL THEN 1 END) / COUNT(*), 1) as weight_pct
FROM breeds_canonical;

-- Sample data
SELECT 
    breed_name,
    breed_slug,
    size_category,
    growth_end_months,
    senior_start_months,
    activity_baseline,
    energy_factor_mod,
    ideal_weight_min_kg,
    ideal_weight_max_kg
FROM breeds_canonical
LIMIT 10;