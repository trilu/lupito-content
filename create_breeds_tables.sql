-- Create breeds_enrichment table for storing enriched data from multiple sources
CREATE TABLE IF NOT EXISTS breeds_enrichment (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL,
    field_name TEXT NOT NULL,
    field_value TEXT,
    field_numeric NUMERIC,
    source TEXT NOT NULL, -- 'wikipedia', 'akc', 'fci', 'manual'
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    confidence_score NUMERIC DEFAULT 1.0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(breed_slug, field_name, source)
);

-- Create indexes
CREATE INDEX idx_breeds_enrichment_slug ON breeds_enrichment(breed_slug);
CREATE INDEX idx_breeds_enrichment_field ON breeds_enrichment(field_name);
CREATE INDEX idx_breeds_enrichment_source ON breeds_enrichment(source);

-- Create breeds_overrides table for manual corrections
CREATE TABLE IF NOT EXISTS breeds_overrides (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL,
    field_name TEXT NOT NULL,
    original_value TEXT,
    override_value TEXT,
    override_reason TEXT NOT NULL,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(breed_slug, field_name)
);

-- Create indexes
CREATE INDEX idx_breeds_overrides_slug ON breeds_overrides(breed_slug);
CREATE INDEX idx_breeds_overrides_applied ON breeds_overrides(applied);

-- Add some initial overrides for known issues
INSERT INTO breeds_overrides (breed_slug, field_name, original_value, override_value, override_reason, created_by, applied)
VALUES
    ('labrador-retriever', 'size_category', 'm', 'l', 'Labrador Retrievers are large dogs (25-36kg)', 'admin', true),
    ('golden-retriever', 'size_category', 'm', 'l', 'Golden Retrievers are large dogs (25-32kg)', 'admin', true),
    ('chihuahua', 'size_category', 's', 'xs', 'Chihuahuas are extra small dogs (1-3kg)', 'admin', true),
    ('great-dane', 'size_category', 'l', 'xl', 'Great Danes are giant dogs (45-90kg)', 'admin', true),
    ('saint-bernard', 'size_category', 'l', 'xl', 'Saint Bernards are giant dogs (65-120kg)', 'admin', true)
ON CONFLICT (breed_slug, field_name) DO NOTHING;

-- Create a function to apply overrides to breeds_published
CREATE OR REPLACE FUNCTION apply_breed_overrides()
RETURNS void AS $$
BEGIN
    -- Apply size_category overrides
    UPDATE breeds_published bp
    SET
        size_category = bo.override_value,
        override_reason = bo.override_reason,
        updated_at = NOW()
    FROM breeds_overrides bo
    WHERE bp.breed_slug = bo.breed_slug
    AND bo.field_name = 'size_category'
    AND bo.applied = true;

    -- Mark overrides as applied with timestamp
    UPDATE breeds_overrides
    SET applied_at = NOW()
    WHERE applied = true
    AND applied_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Create breeds_wikipedia_cache table for storing Wikipedia HTML
CREATE TABLE IF NOT EXISTS breeds_wikipedia_cache (
    id SERIAL PRIMARY KEY,
    breed_slug TEXT NOT NULL UNIQUE,
    wikipedia_url TEXT,
    html_content TEXT,
    extracted_data JSONB,
    gcs_html_path TEXT,
    gcs_json_path TEXT,
    scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index
CREATE INDEX idx_breeds_wikipedia_cache_slug ON breeds_wikipedia_cache(breed_slug);

-- Create view for enriched breeds with all sources combined
CREATE OR REPLACE VIEW breeds_enriched_view AS
WITH latest_enrichments AS (
    SELECT DISTINCT ON (breed_slug, field_name)
        breed_slug,
        field_name,
        field_value,
        field_numeric,
        source,
        confidence_score
    FROM breeds_enrichment
    ORDER BY breed_slug, field_name, confidence_score DESC, fetched_at DESC
),
overrides AS (
    SELECT
        breed_slug,
        field_name,
        override_value as field_value,
        'override' as source,
        2.0 as confidence_score -- Highest confidence for manual overrides
    FROM breeds_overrides
    WHERE applied = true
)
SELECT
    bp.breed_slug,
    bp.display_name,
    bp.size_category,
    COALESCE(o_size.field_value, bp.size_category) as size_category_final,
    COALESCE(o_size.source, bp.size_from) as size_source,
    bp.adult_weight_min_kg,
    bp.adult_weight_max_kg,
    bp.adult_weight_avg_kg,
    COALESCE(e_weight.field_value, bp.weight_from) as weight_source,
    bp.height_min_cm,
    bp.height_max_cm,
    COALESCE(e_height.field_value, bp.height_from) as height_source,
    bp.lifespan_min_years,
    bp.lifespan_max_years,
    bp.lifespan_avg_years,
    COALESCE(e_lifespan.field_value, bp.lifespan_from) as lifespan_source,
    bp.energy,
    COALESCE(e_energy.field_value, 'default') as energy_source,
    bp.data_quality_grade,
    bp.updated_at
FROM breeds_published bp
LEFT JOIN overrides o_size
    ON bp.breed_slug = o_size.breed_slug
    AND o_size.field_name = 'size_category'
LEFT JOIN latest_enrichments e_weight
    ON bp.breed_slug = e_weight.breed_slug
    AND e_weight.field_name = 'weight_source'
LEFT JOIN latest_enrichments e_height
    ON bp.breed_slug = e_height.breed_slug
    AND e_height.field_name = 'height_source'
LEFT JOIN latest_enrichments e_lifespan
    ON bp.breed_slug = e_lifespan.breed_slug
    AND e_lifespan.field_name = 'lifespan_source'
LEFT JOIN latest_enrichments e_energy
    ON bp.breed_slug = e_energy.breed_slug
    AND e_energy.field_name = 'energy_source';

-- Grant permissions
GRANT ALL ON breeds_enrichment TO authenticated;
GRANT ALL ON breeds_overrides TO authenticated;
GRANT ALL ON breeds_wikipedia_cache TO authenticated;
GRANT SELECT ON breeds_enriched_view TO authenticated;