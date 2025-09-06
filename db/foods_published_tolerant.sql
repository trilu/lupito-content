-- Tolerant foods_published view that handles missing nutrition data gracefully
-- This view works even when kcal_per_100g, protein%, fat% are NULL
-- Note: When kcal is null, feeding recommendations (grams/day) will be omitted,
--       but the product can still be recommended based on other attributes

CREATE OR REPLACE VIEW foods_published AS
SELECT 
  id,
  source_domain,
  source_url,
  brand,
  product_name,
  form,
  life_stage,
  
  -- Nutrition fields - nullable to handle missing data
  kcal_per_100g,  -- Can be NULL when not available from API/HTML
  protein_percent,  -- Can be NULL
  fat_percent,  -- Can be NULL
  fiber_percent,  -- Can be NULL
  ash_percent,  -- Can be NULL
  moisture_percent,  -- Can be NULL
  
  ingredients_raw,
  
  -- Compute ingredients_tokens from raw text if not already tokenized
  CASE 
    WHEN ingredients_tokens IS NOT NULL AND array_length(ingredients_tokens, 1) > 0 
    THEN ARRAY(
      SELECT DISTINCT LOWER(TRIM(token))
      FROM UNNEST(ingredients_tokens) AS token
      WHERE TRIM(token) != ''
    )
    WHEN ingredients_raw IS NOT NULL 
    THEN ARRAY(
      SELECT DISTINCT LOWER(TRIM(token))
      FROM UNNEST(
        string_to_array(
          regexp_replace(
            regexp_replace(
              LOWER(ingredients_raw), 
              '\([^)]*\)', '', 'g'  -- Remove parenthetical content
            ),
            '[,;]', ',', 'g'  -- Normalize separators
          ), 
          ','
        )
      ) AS token
      WHERE LENGTH(TRIM(token)) > 2
    )
    ELSE '{}'::text[]
  END AS ingredients_tokens,
  
  -- Compute contains_chicken from ingredients
  CASE 
    WHEN contains_chicken = TRUE THEN TRUE
    WHEN ingredients_raw IS NOT NULL AND (
      ingredients_raw ~* 'chicken' OR
      ingredients_raw ~* 'poultry'
    ) THEN TRUE
    WHEN EXISTS (
      SELECT 1 
      FROM UNNEST(
        COALESCE(
          ingredients_tokens, 
          string_to_array(LOWER(COALESCE(ingredients_raw, '')), ',')
        )
      ) AS token 
      WHERE token LIKE '%chicken%' OR token LIKE '%poultry%'
    ) THEN TRUE
    ELSE FALSE
  END AS contains_chicken,
  
  pack_sizes,
  price_eur,
  
  -- Derive price bucket with safe defaults
  CASE
    WHEN price_eur IS NULL THEN 'mid'  -- Default to mid when unknown
    WHEN price_eur < 30 THEN 'low'
    WHEN price_eur < 60 THEN 'mid'
    ELSE 'high'
  END AS price_bucket,
  
  -- Ensure available_countries always has a value
  COALESCE(
    NULLIF(available_countries, '{}'), 
    ARRAY['EU']::text[]
  ) AS available_countries,
  
  gtin,
  first_seen_at,
  last_seen_at,
  
  -- Add metadata about data completeness
  CASE
    WHEN kcal_per_100g IS NOT NULL 
     AND protein_percent IS NOT NULL 
     AND fat_percent IS NOT NULL
    THEN TRUE
    ELSE FALSE
  END AS has_complete_nutrition,
  
  -- Note when nutrition is missing (for feeding calculations)
  CASE
    WHEN kcal_per_100g IS NULL
    THEN 'Note: Feeding recommendations (grams/day) cannot be calculated without kcal data'
    ELSE NULL
  END AS nutrition_note

FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;

-- Grant appropriate permissions
GRANT SELECT ON foods_published TO anon;
GRANT SELECT ON foods_published TO authenticated;

-- Add comment to the view
COMMENT ON VIEW foods_published IS 
'Tolerant view of food products that handles missing nutrition data. 
When kcal_per_100g is NULL, feeding recommendations (grams/day) will be omitted, 
but products can still be recommended based on ingredients, form, life stage, etc.';

-- Add column comments for clarity
COMMENT ON COLUMN foods_published.kcal_per_100g IS 'Energy content per 100g - may be NULL if not available from source';
COMMENT ON COLUMN foods_published.protein_percent IS 'Protein percentage - may be NULL if not available from source';
COMMENT ON COLUMN foods_published.fat_percent IS 'Fat percentage - may be NULL if not available from source';
COMMENT ON COLUMN foods_published.has_complete_nutrition IS 'TRUE when kcal, protein, and fat are all available';
COMMENT ON COLUMN foods_published.nutrition_note IS 'Informational note when nutrition data is incomplete';