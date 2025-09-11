-- Generated: 2025-09-10 14:57:50
-- Purpose: Check Tables


        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name IN ('foods_published', 'food_candidates', 'food_candidates_sc', 
                     'food_brands', 'foods_enrichment', 'foods_overrides', 'food_raw')
        ORDER BY name
        