-- Script to fix brand anomalies
-- Generated: 2025-09-13 13:03:01.120022
-- Total anomalies: 23

BEGIN;

-- Fix '155444' -> 'IAMS' (11 products)
UPDATE foods_canonical
SET brand = 'IAMS'
WHERE brand = '155444';

-- Fix 'Ci' -> 'Tickety Boo' (11 products)
UPDATE foods_canonical
SET brand = 'Tickety Boo'
WHERE brand = 'Ci';

-- Fix 'Go' -> 'Native' (1 products)
UPDATE foods_canonical
SET brand = 'Native'
WHERE brand = 'Go';

-- Fix products with NULL/empty brand but clear brand in name

-- Verify changes before committing
-- ROLLBACK; -- Uncomment to rollback
-- COMMIT; -- Uncomment to commit
