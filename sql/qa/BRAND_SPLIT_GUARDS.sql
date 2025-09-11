-- ============================================================================
-- BRAND SPLIT GUARDS
-- Purpose: QA guards to ensure no split-brand issues in published views
-- Must all return 0 rows for production deployment
-- ============================================================================

-- Guard 1: No product names starting with orphaned brand fragments
-- This query should return 0 rows
WITH orphan_fragments AS (
    SELECT * FROM (VALUES
        ('Canin', 'royal_canin'),
        ('Science Plan', 'hills'),
        ('Prescription Diet', 'hills'),
        ('Pro Plan', 'purina'),
        ('ONE', 'purina'),
        ('Beta', 'purina'),
        ('N&D', 'farmina'),
        ('Grange', 'arden_grange'),
        ('Kitchen', 'lilys_kitchen'),
        ('Heads', 'barking_heads'),
        ('Core', 'wellness'),
        ('Freedom', 'wild_freedom'),
        ('of the Wild', 'taste_of_the_wild')
    ) AS t(fragment, expected_brand_slug)
)
SELECT 
    'ORPHAN_FRAGMENT' as guard_type,
    brand_slug,
    product_name,
    f.fragment as detected_fragment,
    f.expected_brand_slug,
    'Product name starts with orphaned brand fragment' as issue
FROM foods_published_prod p
CROSS JOIN orphan_fragments f
WHERE 
    -- Check if product_name starts with fragment (word boundary)
    p.product_name ~ ('^' || f.fragment || '\s')
    -- Exclude false positives (e.g., "Canine" is not "Canin")
    AND NOT (f.fragment = 'Canin' AND p.product_name ~ '^Canine\s')
    -- Should be the expected brand if fragment is found
    AND p.brand_slug != f.expected_brand_slug;

-- Guard 2: No incomplete brand slugs (e.g., 'royal' instead of 'royal_canin')
-- This query should return 0 rows
SELECT 
    'INCOMPLETE_SLUG' as guard_type,
    brand_slug,
    brand,
    product_name,
    'Incomplete brand slug detected' as issue
FROM foods_published_prod
WHERE 
    -- Check for incomplete slugs
    (brand_slug = 'royal' AND brand_slug != 'royal_canin')
    OR (brand_slug = 'hills' AND product_name ~ '^(Science Plan|Prescription Diet)')
    OR (brand_slug = 'purina' AND product_name ~ '^(Pro Plan|ONE|Beta)')
    OR (brand_slug = 'arden' AND brand_slug != 'arden_grange')
    OR (brand_slug = 'barking' AND brand_slug != 'barking_heads')
    OR (brand_slug = 'taste' AND brand_slug != 'taste_of_the_wild')
    OR (brand_slug = 'wild' AND brand_slug != 'wild_freedom')
    OR (brand_slug = 'lilys' AND brand_slug != 'lilys_kitchen');

-- Guard 3: No split brand patterns in brand|product_name combination
-- This query should return 0 rows
SELECT 
    'SPLIT_BRAND' as guard_type,
    brand_slug,
    brand,
    product_name,
    CASE
        WHEN brand = 'Royal' AND product_name ~ '^Canin\s' THEN 'Royal|Canin split'
        WHEN brand IN ('Hills', 'Hill''s') AND product_name ~ '^Science Plan\s' THEN 'Hills|Science Plan split'
        WHEN brand IN ('Hills', 'Hill''s') AND product_name ~ '^Prescription Diet\s' THEN 'Hills|Prescription Diet split'
        WHEN brand = 'Purina' AND product_name ~ '^Pro Plan\s' THEN 'Purina|Pro Plan split'
        WHEN brand = 'Purina' AND product_name ~ '^ONE\s' THEN 'Purina|ONE split'
        WHEN brand = 'Arden' AND product_name ~ '^Grange\s' THEN 'Arden|Grange split'
        WHEN brand = 'Barking' AND product_name ~ '^Heads\s' THEN 'Barking|Heads split'
        WHEN brand = 'Taste' AND product_name ~ '^of the Wild\s' THEN 'Taste|of the Wild split'
        WHEN brand = 'Wild' AND product_name ~ '^Freedom\s' THEN 'Wild|Freedom split'
        WHEN brand = 'Lily''s' AND product_name ~ '^Kitchen\s' THEN 'Lily''s|Kitchen split'
        ELSE 'Unknown split pattern'
    END as issue
FROM foods_published_prod
WHERE 
    (brand = 'Royal' AND product_name ~ '^Canin\s')
    OR (brand IN ('Hills', 'Hill''s') AND product_name ~ '^(Science Plan|Prescription Diet)\s')
    OR (brand = 'Purina' AND product_name ~ '^(Pro Plan|ONE|Beta)\s')
    OR (brand = 'Arden' AND product_name ~ '^Grange\s')
    OR (brand = 'Barking' AND product_name ~ '^Heads\s')
    OR (brand = 'Taste' AND product_name ~ '^of the Wild\s')
    OR (brand = 'Wild' AND product_name ~ '^Freedom\s')
    OR (brand = 'Lily''s' AND product_name ~ '^Kitchen\s')
    OR (brand = 'Nature''s' AND product_name ~ '^Variety\s');

-- Guard 4: Check for unexpected product_key collisions
-- This should return only intentional merges
WITH key_counts AS (
    SELECT 
        product_key,
        COUNT(*) as count,
        STRING_AGG(DISTINCT brand_slug, ', ') as brands,
        STRING_AGG(DISTINCT product_name, ' | ' ORDER BY product_name) as names
    FROM foods_published_prod
    GROUP BY product_key
    HAVING COUNT(*) > 1
)
SELECT 
    'KEY_COLLISION' as guard_type,
    product_key,
    count as duplicate_count,
    brands,
    LEFT(names, 100) as sample_names,
    'Unexpected product_key collision' as issue
FROM key_counts
WHERE 
    -- Exclude known/intentional merges
    product_key NOT IN (
        SELECT product_key FROM brand_merge_log
        WHERE merge_approved = true
    );

-- Guard 5: Validate canonical brand slugs are used
-- This query should return 0 rows
SELECT 
    'NON_CANONICAL_SLUG' as guard_type,
    brand_slug,
    brand,
    COUNT(*) as product_count,
    'Non-canonical brand slug in use' as issue
FROM foods_published_prod
WHERE brand_slug IN (
    -- These slugs should not exist (should be canonicalized)
    'royal',  -- Should be 'royal_canin'
    'hills_science_plan',  -- Should be 'hills' with brand_line
    'hills_prescription_diet',  -- Should be 'hills' with brand_line
    'purina_pro_plan',  -- Should be 'purina' with brand_line
    'purina_one',  -- Should be 'purina' with brand_line
    'arden',  -- Should be 'arden_grange'
    'barking',  -- Should be 'barking_heads'
    'taste',  -- Should be 'taste_of_the_wild'
    'lilys',  -- Should be 'lilys_kitchen'
    'natures'  -- Should be 'natures_variety'
)
GROUP BY brand_slug, brand;

-- ============================================================================
-- SUMMARY QUERY - Run this to check all guards at once
-- ============================================================================
WITH all_guards AS (
    -- Combine all guard queries
    SELECT 'ORPHAN_FRAGMENT' as guard_name, COUNT(*) as violations
    FROM foods_published_prod p
    WHERE EXISTS (
        SELECT 1 FROM (VALUES
            ('Canin', 'royal_canin'),
            ('Science Plan', 'hills'),
            ('Grange', 'arden_grange'),
            ('Heads', 'barking_heads')
        ) AS f(fragment, expected_brand_slug)
        WHERE p.product_name ~ ('^' || f.fragment || '\s')
            AND p.brand_slug != f.expected_brand_slug
    )
    
    UNION ALL
    
    SELECT 'SPLIT_BRAND' as guard_name, COUNT(*) as violations
    FROM foods_published_prod
    WHERE (brand = 'Royal' AND product_name ~ '^Canin\s')
        OR (brand = 'Arden' AND product_name ~ '^Grange\s')
        OR (brand = 'Barking' AND product_name ~ '^Heads\s')
    
    UNION ALL
    
    SELECT 'INCOMPLETE_SLUG' as guard_name, COUNT(*) as violations  
    FROM foods_published_prod
    WHERE brand_slug IN ('royal', 'arden', 'barking', 'taste', 'lilys')
    
    UNION ALL
    
    SELECT 'KEY_COLLISION' as guard_name, COUNT(*) as violations
    FROM (
        SELECT product_key
        FROM foods_published_prod
        GROUP BY product_key
        HAVING COUNT(*) > 1
    ) t
)
SELECT 
    guard_name,
    violations,
    CASE 
        WHEN violations = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END as status
FROM all_guards
ORDER BY violations DESC;

-- ============================================================================
-- CI/CD GUARD - Single query for automated checking
-- Should return exactly 1 row with violations = 0 and status = 'PASS'
-- ============================================================================
SELECT 
    CASE 
        WHEN SUM(violations) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END as overall_status,
    SUM(violations) as total_violations,
    STRING_AGG(
        CASE WHEN violations > 0 
        THEN guard_name || '(' || violations || ')' 
        END, ', '
    ) as failed_guards
FROM (
    SELECT 'ORPHAN_FRAGMENTS' as guard_name,
        (SELECT COUNT(*) FROM foods_published_prod 
         WHERE product_name ~ '^(Canin|Grange|Heads|Science Plan|Pro Plan)\s') as violations
    
    UNION ALL
    
    SELECT 'SPLIT_BRANDS' as guard_name,
        (SELECT COUNT(*) FROM foods_published_prod 
         WHERE (brand = 'Arden' AND product_name ~ '^Grange\s')
            OR (brand = 'Barking' AND product_name ~ '^Heads\s')) as violations
    
    UNION ALL
    
    SELECT 'INCOMPLETE_SLUGS' as guard_name,
        (SELECT COUNT(*) FROM foods_published_prod 
         WHERE brand_slug IN ('royal', 'arden', 'barking')) as violations
) guards;