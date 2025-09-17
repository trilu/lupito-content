-- ============================================
-- INITIAL BREED OVERRIDES
-- Known issues to fix manually
-- ============================================

-- Insert initial overrides for known size category issues
INSERT INTO breeds_overrides (breed_slug, field_name, original_value, override_value, override_reason, created_by, applied)
VALUES
    -- Large dogs incorrectly marked as medium
    ('labrador-retriever', 'size_category', 'm', 'l', 'Labrador Retrievers are large dogs (25-36kg)', 'system', true),
    ('golden-retriever', 'size_category', 'm', 'l', 'Golden Retrievers are large dogs (25-32kg)', 'system', true),
    ('german-shepherd', 'size_category', 'm', 'l', 'German Shepherds are large dogs (22-40kg)', 'system', true),
    ('rottweiler', 'size_category', 'm', 'l', 'Rottweilers are large dogs (35-60kg)', 'system', true),
    ('doberman-pinscher', 'size_category', 'm', 'l', 'Doberman Pinschers are large dogs (27-45kg)', 'system', true),

    -- Extra small dogs incorrectly marked as small
    ('chihuahua', 'size_category', 's', 'xs', 'Chihuahuas are extra small dogs (1-3kg)', 'system', true),
    ('yorkshire-terrier', 'size_category', 's', 'xs', 'Yorkshire Terriers are extra small dogs (2-3kg)', 'system', true),
    ('maltese', 'size_category', 's', 'xs', 'Maltese are extra small dogs (3-4kg)', 'system', true),
    ('pomeranian', 'size_category', 's', 'xs', 'Pomeranians are extra small dogs (1.5-3kg)', 'system', true),

    -- Giant dogs incorrectly marked as large
    ('great-dane', 'size_category', 'l', 'xl', 'Great Danes are giant dogs (45-90kg)', 'system', true),
    ('saint-bernard', 'size_category', 'l', 'xl', 'Saint Bernards are giant dogs (65-120kg)', 'system', true),
    ('mastiff', 'size_category', 'l', 'xl', 'Mastiffs are giant dogs (70-100kg)', 'system', true),
    ('newfoundland', 'size_category', 'l', 'xl', 'Newfoundlands are giant dogs (50-70kg)', 'system', true),
    ('irish-wolfhound', 'size_category', 'l', 'xl', 'Irish Wolfhounds are giant dogs (40-70kg)', 'system', true),
    ('great-pyrenees', 'size_category', 'l', 'xl', 'Great Pyrenees are giant dogs (40-65kg)', 'system', true)
ON CONFLICT (breed_slug, field_name) DO UPDATE
SET
    override_value = EXCLUDED.override_value,
    override_reason = EXCLUDED.override_reason,
    applied = EXCLUDED.applied,
    updated_at = NOW();

-- Apply the overrides to breeds_published
UPDATE breeds_published bp
SET
    size_category = bo.override_value,
    override_reason = bo.override_reason,
    size_from = 'override',
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