-- ============================================
-- ADD MANUAL BREED OVERRIDES
-- For known issues with size categories
-- ============================================

-- Insert or update size category overrides for breeds we know are wrong
-- Using the existing breeds_overrides table structure

-- Large dogs that might be marked as medium
INSERT INTO breeds_overrides (breed_slug, size_category, override_reason, created_at, updated_at)
VALUES
    ('labrador-retriever', 'l', 'Labrador Retrievers are large dogs (25-36kg)', NOW(), NOW()),
    ('golden-retriever', 'l', 'Golden Retrievers are large dogs (25-32kg)', NOW(), NOW()),
    ('german-shepherd', 'l', 'German Shepherds are large dogs (22-40kg)', NOW(), NOW()),
    ('rottweiler', 'l', 'Rottweilers are large dogs (35-60kg)', NOW(), NOW()),
    ('doberman-pinscher', 'l', 'Doberman Pinschers are large dogs (27-45kg)', NOW(), NOW()),
    ('boxer', 'l', 'Boxers are large dogs (25-32kg)', NOW(), NOW()),
    ('standard-poodle', 'l', 'Standard Poodles are large dogs (20-32kg)', NOW(), NOW())
ON CONFLICT (breed_slug) DO UPDATE
SET
    size_category = EXCLUDED.size_category,
    override_reason = EXCLUDED.override_reason,
    updated_at = NOW();

-- Extra small dogs that might be marked as small
INSERT INTO breeds_overrides (breed_slug, size_category, override_reason, created_at, updated_at)
VALUES
    ('chihuahua', 'xs', 'Chihuahuas are extra small dogs (1-3kg)', NOW(), NOW()),
    ('yorkshire-terrier', 'xs', 'Yorkshire Terriers are extra small dogs (2-3kg)', NOW(), NOW()),
    ('maltese', 'xs', 'Maltese are extra small dogs (3-4kg)', NOW(), NOW()),
    ('pomeranian', 'xs', 'Pomeranians are extra small dogs (1.5-3kg)', NOW(), NOW()),
    ('papillon', 'xs', 'Papillons are extra small dogs (3-4.5kg)', NOW(), NOW()),
    ('toy-poodle', 'xs', 'Toy Poodles are extra small dogs (2-4kg)', NOW(), NOW())
ON CONFLICT (breed_slug) DO UPDATE
SET
    size_category = EXCLUDED.size_category,
    override_reason = EXCLUDED.override_reason,
    updated_at = NOW();

-- Giant dogs that might be marked as large
INSERT INTO breeds_overrides (breed_slug, size_category, override_reason, created_at, updated_at)
VALUES
    ('great-dane', 'xl', 'Great Danes are giant dogs (45-90kg)', NOW(), NOW()),
    ('saint-bernard', 'xl', 'Saint Bernards are giant dogs (65-120kg)', NOW(), NOW()),
    ('mastiff', 'xl', 'Mastiffs are giant dogs (70-100kg)', NOW(), NOW()),
    ('english-mastiff', 'xl', 'English Mastiffs are giant dogs (70-100kg)', NOW(), NOW()),
    ('newfoundland', 'xl', 'Newfoundlands are giant dogs (50-70kg)', NOW(), NOW()),
    ('irish-wolfhound', 'xl', 'Irish Wolfhounds are giant dogs (40-70kg)', NOW(), NOW()),
    ('great-pyrenees', 'xl', 'Great Pyrenees are giant dogs (40-65kg)', NOW(), NOW()),
    ('bernese-mountain-dog', 'xl', 'Bernese Mountain Dogs are giant dogs (35-55kg)', NOW(), NOW()),
    ('leonberger', 'xl', 'Leonbergers are giant dogs (45-77kg)', NOW(), NOW()),
    ('tibetan-mastiff', 'xl', 'Tibetan Mastiffs are giant dogs (35-75kg)', NOW(), NOW())
ON CONFLICT (breed_slug) DO UPDATE
SET
    size_category = EXCLUDED.size_category,
    override_reason = EXCLUDED.override_reason,
    updated_at = NOW();

-- Check what breeds have overrides
SELECT
    breed_slug,
    size_category,
    override_reason
FROM breeds_overrides
WHERE size_category IS NOT NULL
ORDER BY
    CASE size_category
        WHEN 'xs' THEN 1
        WHEN 's' THEN 2
        WHEN 'm' THEN 3
        WHEN 'l' THEN 4
        WHEN 'xl' THEN 5
    END,
    breed_slug;