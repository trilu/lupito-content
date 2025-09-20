-- ============================================
-- ADD BREED_SLUG TO BREEDS TABLE
-- Copy existing breed_slugs from breeds_published to ensure perfect matching
-- ============================================

-- Step 1: Add breed_slug column to breeds table
ALTER TABLE breeds
ADD COLUMN IF NOT EXISTS breed_slug TEXT;

-- Step 2: Create index on the new column for performance
CREATE INDEX IF NOT EXISTS idx_breeds_breed_slug ON breeds(breed_slug);

-- Step 3: Copy breed_slugs from breeds_published by matching on name
-- First, try exact name matches
UPDATE breeds b
SET breed_slug = bp.breed_slug
FROM breeds_published bp
WHERE b.breed_slug IS NULL
  AND (
    LOWER(REPLACE(b.name_en, ' ', '-')) = LOWER(REPLACE(bp.display_name, ' ', '-'))
    OR LOWER(b.name_en) = LOWER(bp.display_name)
  );

-- Step 3b: Try matching with breeds_comprehensive_content as well
UPDATE breeds b
SET breed_slug = bcc.breed_slug
FROM breeds_comprehensive_content bcc
WHERE b.breed_slug IS NULL
  AND EXISTS (
    SELECT 1 FROM breeds_published bp
    WHERE bp.breed_slug = bcc.breed_slug
  )
  AND (
    LOWER(REPLACE(b.name_en, ' ', '-')) = LOWER(REPLACE(bcc.breed_slug, '-', ' '))
    OR LOWER(REPLACE(b.name_en, '-', ' ')) = LOWER(REPLACE(bcc.breed_slug, '-', ' '))
  );

-- Step 4: Show some examples of the mapping
DO $$
DECLARE
    rec RECORD;
    match_count INTEGER := 0;
    total_count INTEGER := 0;
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'BREED SLUG MAPPING EXAMPLES';
    RAISE NOTICE '========================================';

    -- Show first 10 mappings
    FOR rec IN
        SELECT name_en, breed_slug
        FROM breeds
        LIMIT 10
    LOOP
        RAISE NOTICE '% → %', rec.name_en, rec.breed_slug;
    END LOOP;

    -- Count how many will match with breeds_published
    SELECT COUNT(*) INTO total_count FROM breeds WHERE breed_slug IS NOT NULL;

    SELECT COUNT(DISTINCT b.breed_slug)
    INTO match_count
    FROM breeds b
    INNER JOIN breeds_published bp ON b.breed_slug = bp.breed_slug;

    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MATCHING STATISTICS';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total breeds with slugs: %', total_count;
    RAISE NOTICE 'Breeds matching breeds_published: %', match_count;
    RAISE NOTICE 'Match rate: %.1f%%', (match_count::NUMERIC / total_count * 100);
END $$;

-- Step 5: Handle special cases by looking up specific breed names
-- Use subqueries to get the actual breed_slug from breeds_published
DO $$
BEGIN
    -- German Shepherd variations
    UPDATE breeds b
    SET breed_slug = (
        SELECT breed_slug FROM breeds_published
        WHERE breed_slug = 'german-shepherd'
        LIMIT 1
    )
    WHERE b.breed_slug IS NULL
      AND LOWER(b.name_en) IN ('german shepherd dog', 'german shepard', 'alsatian', 'german shepherd');

    -- Labrador variations
    UPDATE breeds b
    SET breed_slug = (
        SELECT breed_slug FROM breeds_published
        WHERE breed_slug = 'labrador-retriever'
        LIMIT 1
    )
    WHERE b.breed_slug IS NULL
      AND LOWER(b.name_en) IN ('labrador', 'lab', 'labrador retriever');

    -- Golden Retriever variations
    UPDATE breeds b
    SET breed_slug = (
        SELECT breed_slug FROM breeds_published
        WHERE breed_slug = 'golden-retriever'
        LIMIT 1
    )
    WHERE b.breed_slug IS NULL
      AND LOWER(b.name_en) IN ('golden retriever', 'golden');

    -- Bulldog variations
    UPDATE breeds b
    SET breed_slug = (
        SELECT breed_slug FROM breeds_published
        WHERE breed_slug = 'french-bulldog'
        LIMIT 1
    )
    WHERE b.breed_slug IS NULL
      AND LOWER(b.name_en) IN ('french bulldog', 'frenchie', 'bouledogue francais');

    UPDATE breeds b
    SET breed_slug = (
        SELECT breed_slug FROM breeds_published
        WHERE breed_slug = 'english-bulldog'
        LIMIT 1
    )
    WHERE b.breed_slug IS NULL
      AND LOWER(b.name_en) IN ('english bulldog', 'british bulldog', 'bulldog');

    RAISE NOTICE 'Applied common breed name variations using actual slugs from breeds_published';
END $$;

-- Step 6: Verify the improvement
SELECT
    'Breed slug addition complete' as status,
    COUNT(*) as total_breeds,
    COUNT(breed_slug) as with_slugs,
    COUNT(DISTINCT breed_slug) as unique_slugs
FROM breeds;