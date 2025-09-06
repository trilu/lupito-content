-- Enhanced foods_published view with price_per_kg calculation
-- Tolerant of missing nutrition data and computes price metrics

CREATE OR REPLACE VIEW foods_published AS
SELECT 
  id,
  source_domain,
  source_url,
  brand,
  product_name,
  form,
  life_stage,
  
  -- Nutrition fields - nullable
  kcal_per_100g,
  protein_percent,
  fat_percent,
  fiber_percent,
  ash_percent,
  moisture_percent,
  
  ingredients_raw,
  
  -- Compute ingredients_tokens
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
              '\([^)]*\)', '', 'g'
            ),
            '[,;]', ',', 'g'
          ), 
          ','
        )
      ) AS token
      WHERE LENGTH(TRIM(token)) > 2
    )
    ELSE '{}'::text[]
  END AS ingredients_tokens,
  
  -- Compute contains_chicken
  CASE 
    WHEN contains_chicken = TRUE THEN TRUE
    WHEN ingredients_raw IS NOT NULL AND (
      ingredients_raw ~* 'chicken' OR
      ingredients_raw ~* 'poultry'
    ) THEN TRUE
    ELSE FALSE
  END AS contains_chicken,
  
  pack_sizes,
  price_eur,
  
  -- Calculate price per kg from smallest pack size and price
  -- Assumes pack_sizes contains strings like "1.5kg", "400g", etc.
  CASE
    WHEN price_eur IS NOT NULL AND pack_sizes IS NOT NULL AND array_length(pack_sizes, 1) > 0
    THEN (
      -- Extract first pack size and convert to kg
      SELECT price_eur / NULLIF(
        CASE
          -- Handle kg units
          WHEN pack_sizes[1] ~* '\d+(\.\d+)?\s*kg'
          THEN CAST(
            regexp_replace(pack_sizes[1], '[^0-9.]', '', 'g')
            AS NUMERIC
          )
          -- Handle g units (convert to kg)
          WHEN pack_sizes[1] ~* '\d+(\.\d+)?\s*g'
          THEN CAST(
            regexp_replace(pack_sizes[1], '[^0-9.]', '', 'g')
            AS NUMERIC
          ) / 1000.0
          ELSE NULL
        END,
        0
      )
    )
    ELSE NULL
  END AS price_per_kg,
  
  -- Original price bucket based on total price
  CASE
    WHEN price_eur IS NULL THEN 'mid'
    WHEN price_eur < 30 THEN 'low'
    WHEN price_eur < 60 THEN 'mid'
    ELSE 'high'
  END AS price_bucket,
  
  -- New price bucket based on price per kg
  -- Thresholds: <3 EUR/kg = low, 3-6 EUR/kg = mid, >6 EUR/kg = high
  CASE
    WHEN price_eur IS NULL OR pack_sizes IS NULL OR array_length(pack_sizes, 1) = 0
    THEN 'mid'  -- Default when can't calculate
    ELSE (
      SELECT CASE
        WHEN price_per_kg < 3 THEN 'low'
        WHEN price_per_kg < 6 THEN 'mid'
        ELSE 'high'
      END
      FROM (
        SELECT price_eur / NULLIF(
          CASE
            WHEN pack_sizes[1] ~* '\d+(\.\d+)?\s*kg'
            THEN CAST(regexp_replace(pack_sizes[1], '[^0-9.]', '', 'g') AS NUMERIC)
            WHEN pack_sizes[1] ~* '\d+(\.\d+)?\s*g'
            THEN CAST(regexp_replace(pack_sizes[1], '[^0-9.]', '', 'g') AS NUMERIC) / 1000.0
            ELSE NULL
          END,
          0
        ) AS price_per_kg
      ) calc
    )
  END AS price_per_kg_bucket,
  
  -- Available countries with default
  COALESCE(
    NULLIF(available_countries, '{}'), 
    ARRAY['EU']::text[]
  ) AS available_countries,
  
  gtin,
  first_seen_at,
  last_seen_at,
  
  -- Data completeness flag
  CASE
    WHEN kcal_per_100g IS NOT NULL 
     AND protein_percent IS NOT NULL 
     AND fat_percent IS NOT NULL
    THEN TRUE
    ELSE FALSE
  END AS has_complete_nutrition

FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;

-- Grant permissions
GRANT SELECT ON foods_published TO anon;
GRANT SELECT ON foods_published TO authenticated;

-- Add comments
COMMENT ON VIEW foods_published IS 
'Enhanced view with price_per_kg calculation. 
Price buckets based on EUR/kg: <3 = low, 3-6 = mid, >6 = high.
When kcal_per_100g is NULL, feeding recommendations (grams/day) cannot be calculated.';

COMMENT ON COLUMN foods_published.price_per_kg IS 'Price per kilogram calculated from price_eur and first pack size';
COMMENT ON COLUMN foods_published.price_per_kg_bucket IS 'Price category based on EUR/kg: low (<3), mid (3-6), high (>6)';