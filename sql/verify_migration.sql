-- ============================================
-- VERIFICATION QUERIES
-- Run this AFTER executing schema_patch_execute.sql
-- ============================================

-- 1. Check which new columns were successfully added
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 
    'ingredients_source', 
    'ingredients_parsed_at',
    'ingredients_language', 
    'fiber_percent', 
    'ash_percent', 
    'moisture_percent', 
    'macros_source', 
    'kcal_source'
)
ORDER BY column_name;

-- 2. Count summary
SELECT 
    COUNT(*) as new_columns_added,
    COUNT(*) FILTER (WHERE column_name LIKE 'ingredients_%') as ingredients_columns,
    COUNT(*) FILTER (WHERE column_name LIKE '%_percent') as nutrition_columns,
    COUNT(*) FILTER (WHERE column_name LIKE '%_source') as source_columns
FROM information_schema.columns
WHERE table_name = 'foods_canonical'
AND column_name IN (
    'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
    'ingredients_language', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
);

-- 3. Check if views can see the new columns
SELECT 
    'foods_published' as view_name,
    bool_or(column_name = 'ingredients_raw') as has_ingredients_raw,
    bool_or(column_name = 'fiber_percent') as has_fiber_percent,
    bool_or(column_name = 'ash_percent') as has_ash_percent,
    bool_or(column_name = 'moisture_percent') as has_moisture_percent,
    bool_or(column_name = 'macros_source') as has_macros_source,
    bool_or(column_name = 'kcal_source') as has_kcal_source
FROM information_schema.columns
WHERE table_name = 'foods_published'
AND column_name IN (
    'ingredients_raw', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
)

UNION ALL

SELECT 
    'foods_published_preview',
    bool_or(column_name = 'ingredients_raw'),
    bool_or(column_name = 'fiber_percent'),
    bool_or(column_name = 'ash_percent'),
    bool_or(column_name = 'moisture_percent'),
    bool_or(column_name = 'macros_source'),
    bool_or(column_name = 'kcal_source')
FROM information_schema.columns
WHERE table_name = 'foods_published_preview'
AND column_name IN (
    'ingredients_raw', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
)

UNION ALL

SELECT 
    'foods_published_prod',
    bool_or(column_name = 'ingredients_raw'),
    bool_or(column_name = 'fiber_percent'),
    bool_or(column_name = 'ash_percent'),
    bool_or(column_name = 'moisture_percent'),
    bool_or(column_name = 'macros_source'),
    bool_or(column_name = 'kcal_source')
FROM information_schema.columns
WHERE table_name = 'foods_published_prod'
AND column_name IN (
    'ingredients_raw', 'fiber_percent', 'ash_percent', 
    'moisture_percent', 'macros_source', 'kcal_source'
);

-- 4. Test query with new columns
SELECT 
    product_key,
    brand_slug,
    ingredients_raw,
    fiber_percent,
    ash_percent,
    moisture_percent,
    macros_source,
    kcal_source
FROM foods_canonical
LIMIT 3;

-- 5. Check indexes
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'foods_canonical'
AND (
    indexname LIKE '%ingredients_source%' 
    OR indexname LIKE '%macros_source%' 
    OR indexname LIKE '%kcal_source%'
    OR indexname LIKE '%missing%'
)
ORDER BY indexname;

-- 6. Final summary
WITH col_check AS (
    SELECT COUNT(*) as total_new_columns
    FROM information_schema.columns
    WHERE table_name = 'foods_canonical'
    AND column_name IN (
        'ingredients_raw', 'ingredients_source', 'ingredients_parsed_at',
        'ingredients_language', 'fiber_percent', 'ash_percent', 
        'moisture_percent', 'macros_source', 'kcal_source'
    )
),
idx_check AS (
    SELECT COUNT(*) as total_new_indexes
    FROM pg_indexes
    WHERE tablename = 'foods_canonical'
    AND indexname IN (
        'idx_foods_canonical_ingredients_source',
        'idx_foods_canonical_macros_source',
        'idx_foods_canonical_kcal_source',
        'idx_foods_canonical_missing_ingredients',
        'idx_foods_canonical_missing_macros',
        'idx_foods_canonical_missing_fiber'
    )
)
SELECT 
    c.total_new_columns,
    i.total_new_indexes,
    CASE 
        WHEN c.total_new_columns = 9 AND i.total_new_indexes = 6 
        THEN '✅ MIGRATION FULLY SUCCESSFUL'
        WHEN c.total_new_columns > 0 
        THEN '⚠️ PARTIAL SUCCESS - Check details above'
        ELSE '❌ MIGRATION FAILED'
    END as status
FROM col_check c, idx_check i;