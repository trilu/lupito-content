-- ============================================================================
-- MILESTONE 1: Compatibility Views for Canonical Schema
-- ============================================================================
-- This script creates two compatibility views that project food_candidates and
-- food_brands tables into the canonical schema required by the AI service.
--
-- Required canonical fields:
-- id, brand, name, form, life_stage, ingredients_tokens, contains_chicken,
-- kcal_per_100g, protein_percent, fat_percent, price_per_kg, price_bucket,
-- available_countries, image_public_url, first_seen_at, last_seen_at, source_domain
-- ============================================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS food_candidates_compat CASCADE;
DROP VIEW IF EXISTS food_brands_compat CASCADE;

-- ============================================================================
-- HELPER FUNCTIONS FOR NORMALIZATION
-- ============================================================================

-- Normalize form to: dry|wet|freeze_dried|raw|any
CREATE OR REPLACE FUNCTION normalize_form(input TEXT) RETURNS TEXT AS $$
BEGIN
    IF input IS NULL OR TRIM(input) = '' THEN
        RETURN 'any';
    END IF;
    
    RETURN CASE 
        WHEN LOWER(input) LIKE '%dry%' THEN 'dry'
        WHEN LOWER(input) LIKE '%wet%' OR LOWER(input) LIKE '%can%' OR LOWER(input) LIKE '%pouch%' THEN 'wet'
        WHEN LOWER(input) LIKE '%freeze%' OR LOWER(input) LIKE '%dried%' THEN 'freeze_dried'
        WHEN LOWER(input) LIKE '%raw%' OR LOWER(input) LIKE '%frozen%' THEN 'raw'
        ELSE 'any'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Normalize life_stage to: puppy|adult|senior|all
CREATE OR REPLACE FUNCTION normalize_life_stage(input TEXT) RETURNS TEXT AS $$
BEGIN
    IF input IS NULL OR TRIM(input) = '' THEN
        RETURN 'all';
    END IF;
    
    RETURN CASE 
        WHEN LOWER(input) LIKE '%puppy%' OR LOWER(input) LIKE '%junior%' THEN 'puppy'
        WHEN LOWER(input) LIKE '%adult%' THEN 'adult'
        WHEN LOWER(input) LIKE '%senior%' OR LOWER(input) LIKE '%mature%' THEN 'senior'
        WHEN LOWER(input) LIKE '%all%' THEN 'all'
        ELSE 'all'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Tokenize ingredients from raw text
CREATE OR REPLACE FUNCTION tokenize_ingredients(raw_text TEXT) RETURNS TEXT[] AS $$
DECLARE
    tokens TEXT[];
    cleaned TEXT;
BEGIN
    IF raw_text IS NULL OR TRIM(raw_text) = '' THEN
        RETURN '{}';
    END IF;
    
    -- Clean and split by common separators
    cleaned := LOWER(regexp_replace(raw_text, '[,;()]', ' ', 'g'));
    cleaned := regexp_replace(cleaned, '\s+', ' ', 'g');
    tokens := string_to_array(TRIM(cleaned), ' ');
    
    -- Remove empty strings
    tokens := ARRAY(SELECT token FROM unnest(tokens) AS token WHERE LENGTH(TRIM(token)) > 0);
    
    RETURN COALESCE(tokens, '{}');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Check if ingredients contain chicken
CREATE OR REPLACE FUNCTION contains_chicken_check(tokens TEXT[]) RETURNS BOOLEAN AS $$
BEGIN
    IF tokens IS NULL OR array_length(tokens, 1) IS NULL THEN
        RETURN FALSE;
    END IF;
    
    RETURN EXISTS (
        SELECT 1 
        FROM unnest(tokens) AS token
        WHERE token ILIKE '%chicken%' 
           OR token ILIKE '%poultry%'
           OR token ILIKE '%fowl%'
           OR token ILIKE '%hen%'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Derive price bucket from price
CREATE OR REPLACE FUNCTION derive_price_bucket(price_eur NUMERIC) RETURNS TEXT AS $$
BEGIN
    RETURN CASE
        WHEN price_eur IS NULL THEN 'mid'
        WHEN price_eur < 3 THEN 'low'
        WHEN price_eur < 6 THEN 'mid'
        ELSE 'high'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate price per kg from price and pack sizes
CREATE OR REPLACE FUNCTION calculate_price_per_kg(price_eur NUMERIC, pack_sizes TEXT[]) RETURNS NUMERIC AS $$
DECLARE
    avg_size_g NUMERIC;
    size_values NUMERIC[];
    size_text TEXT;
BEGIN
    IF price_eur IS NULL THEN
        RETURN NULL;
    END IF;
    
    IF pack_sizes IS NULL OR array_length(pack_sizes, 1) IS NULL THEN
        RETURN price_eur; -- Assume 1kg if no size info
    END IF;
    
    -- Extract numeric values from pack sizes
    size_values := ARRAY[]::NUMERIC[];
    FOREACH size_text IN ARRAY pack_sizes
    LOOP
        -- Extract number from strings like "2kg", "400g", "2.5kg"
        IF size_text ~ '[0-9]' THEN
            -- Convert to grams
            IF LOWER(size_text) LIKE '%kg%' THEN
                size_values := array_append(size_values, 
                    CAST(regexp_replace(size_text, '[^0-9.]', '', 'g') AS NUMERIC) * 1000);
            ELSIF LOWER(size_text) LIKE '%g%' THEN
                size_values := array_append(size_values, 
                    CAST(regexp_replace(size_text, '[^0-9.]', '', 'g') AS NUMERIC));
            END IF;
        END IF;
    END LOOP;
    
    -- Calculate average size
    IF array_length(size_values, 1) > 0 THEN
        avg_size_g := (SELECT AVG(val) FROM unnest(size_values) AS val);
        IF avg_size_g > 0 THEN
            RETURN price_eur * 1000.0 / avg_size_g;
        END IF;
    END IF;
    
    RETURN price_eur; -- Default to assuming 1kg
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- FOOD_CANDIDATES_COMPAT VIEW
-- ============================================================================
CREATE VIEW food_candidates_compat AS
SELECT 
    -- Identity
    id::TEXT as id,
    TRIM(COALESCE(brand, 'Unknown')) as brand,
    TRIM(COALESCE(product_name, 'Unknown Product')) as name,
    
    -- Product characteristics - with normalization
    normalize_form(COALESCE(form, ingredients_raw)) as form,
    normalize_life_stage(COALESCE(life_stage, ingredients_raw)) as life_stage,
    
    -- Ingredients
    COALESCE(
        ingredients_tokens,
        tokenize_ingredients(ingredients_raw),
        '{}'::TEXT[]
    ) as ingredients_tokens,
    
    COALESCE(
        contains_chicken,
        contains_chicken_check(COALESCE(ingredients_tokens, tokenize_ingredients(ingredients_raw))),
        FALSE
    ) as contains_chicken,
    
    -- Nutrition
    kcal_per_100g,
    protein_percent,
    fat_percent,
    
    -- Pricing
    calculate_price_per_kg(price_eur, pack_sizes) as price_per_kg,
    derive_price_bucket(price_eur) as price_bucket,
    
    -- Availability
    COALESCE(available_countries, ARRAY['EU']::TEXT[]) as available_countries,
    
    -- Media
    image_url as image_public_url,
    
    -- Metadata
    COALESCE(first_seen_at, NOW()) as first_seen_at,
    COALESCE(last_seen_at, NOW()) as last_seen_at,
    COALESCE(source_domain, 'unknown') as source_domain
    
FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;

-- ============================================================================
-- FOOD_BRANDS_COMPAT VIEW
-- ============================================================================
CREATE VIEW food_brands_compat AS
SELECT 
    -- Identity
    id::TEXT as id,
    TRIM(COALESCE(brand_name, 'Unknown')) as brand,
    TRIM(COALESCE(product_name, 'Unknown Product')) as name,
    
    -- Product characteristics - with normalization
    normalize_form(product_type) as form,
    normalize_life_stage(life_stage) as life_stage,
    
    -- Ingredients
    COALESCE(
        main_ingredients,
        '{}'::TEXT[]
    ) as ingredients_tokens,
    
    contains_chicken_check(main_ingredients) as contains_chicken,
    
    -- Nutrition (limited data available)
    NULL::NUMERIC as kcal_per_100g,  -- Not available in food_brands
    protein_percent::NUMERIC as protein_percent,
    fat_percent::NUMERIC as fat_percent,
    
    -- Pricing (not available)
    NULL::NUMERIC as price_per_kg,
    'mid'::TEXT as price_bucket,  -- Default to mid
    
    -- Availability
    CASE 
        WHEN country_of_origin IS NOT NULL THEN
            ARRAY[country_of_origin]::TEXT[]
        ELSE
            ARRAY['EU']::TEXT[]
    END as available_countries,
    
    -- Media
    NULL::TEXT as image_public_url,  -- Not available in food_brands
    
    -- Metadata
    COALESCE(created_at, NOW()) as first_seen_at,
    COALESCE(created_at, NOW()) as last_seen_at,
    'internal'::TEXT as source_domain
    
FROM food_brands
WHERE brand_name IS NOT NULL 
  AND product_name IS NOT NULL;

-- ============================================================================
-- SANITY CHECK QUERIES
-- ============================================================================
-- Run these queries to verify the views are working:

-- Check food_candidates_compat count
-- SELECT COUNT(*) as food_candidates_count FROM food_candidates_compat;

-- Check food_brands_compat count  
-- SELECT COUNT(*) as food_brands_count FROM food_brands_compat;

-- Sample records from food_candidates_compat
-- SELECT brand, name, form, life_stage, price_bucket, source_domain 
-- FROM food_candidates_compat 
-- LIMIT 5;

-- Sample records from food_brands_compat
-- SELECT brand, name, form, life_stage, price_bucket, source_domain 
-- FROM food_brands_compat 
-- LIMIT 5;

-- Check form distribution
-- SELECT form, COUNT(*) 
-- FROM food_candidates_compat 
-- GROUP BY form 
-- ORDER BY COUNT(*) DESC;

-- Check life_stage distribution
-- SELECT life_stage, COUNT(*) 
-- FROM food_candidates_compat 
-- GROUP BY life_stage 
-- ORDER BY COUNT(*) DESC;

-- Check price_bucket distribution
-- SELECT price_bucket, COUNT(*) 
-- FROM food_candidates_compat 
-- GROUP BY price_bucket 
-- ORDER BY price_bucket;