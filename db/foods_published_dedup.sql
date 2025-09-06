-- Updated foods_published view with dedup preference logic
-- Prefers rows with kcal_per_100g present when same brand+product exists from multiple sources
-- Adds source_domain to show which source "won" the deduplication

CREATE OR REPLACE VIEW foods_published AS
WITH deduplication_ranked AS (
  SELECT 
    *,
    -- Create normalized slugs for grouping
    LOWER(TRIM(REGEXP_REPLACE(brand, '[^a-zA-Z0-9]+', '-', 'g'))) AS brand_slug,
    LOWER(TRIM(REGEXP_REPLACE(product_name, '[^a-zA-Z0-9]+', '-', 'g'))) AS name_slug,
    
    -- Rank rows within each product group, preferring those with kcal
    ROW_NUMBER() OVER (
      PARTITION BY 
        LOWER(TRIM(REGEXP_REPLACE(brand, '[^a-zA-Z0-9]+', '-', 'g'))),
        LOWER(TRIM(REGEXP_REPLACE(product_name, '[^a-zA-Z0-9]+', '-', 'g')))
      ORDER BY 
        -- Primary: prefer rows with kcal_per_100g
        (kcal_per_100g IS NOT NULL) DESC,
        -- Secondary: prefer rows with more nutrition data
        (protein_percent IS NOT NULL)::int + (fat_percent IS NOT NULL)::int + (fiber_percent IS NOT NULL)::int DESC,
        -- Tertiary: last_seen_at (most recent)
        last_seen_at DESC
    ) AS dedup_rank
  FROM food_candidates
  WHERE brand IS NOT NULL 
    AND product_name IS NOT NULL
)
SELECT 
  id,
  source_domain,  -- Now shows which source "won" the deduplication
  source_url,
  brand,
  product_name,
  form,
  life_stage,
  
  -- Nutrition fields - nullable to handle missing data
  kcal_per_100g,  -- Preferred rows with this field will be selected first
  protein_percent,
  fat_percent,
  fiber_percent,
  ash_percent,
  moisture_percent,
  kcal_basis,  -- Track whether energy is measured or estimated
  
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
  
  -- Calculate price_per_kg when possible
  CASE 
    WHEN pack_sizes IS NOT NULL AND array_length(pack_sizes, 1) > 0 AND price_eur IS NOT NULL
    THEN ROUND(
      (price_eur / 
        GREATEST(
          (SELECT AVG((size->>'weight_kg')::numeric) 
           FROM UNNEST(pack_sizes) AS size 
           WHERE (size->>'weight_kg')::numeric > 0),
          0.1  -- Minimum 0.1kg to avoid division errors
        )
      )::numeric, 2
    )
    ELSE NULL
  END AS price_per_kg,
  
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
  quality_rating,  -- Include rating from AADF
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
  END AS nutrition_note,
  
  -- Add dedup metadata for debugging
  brand_slug,
  name_slug

FROM deduplication_ranked
WHERE dedup_rank = 1  -- Only select the highest-ranked row per product
ORDER BY brand, product_name;

-- Grant appropriate permissions
GRANT SELECT ON foods_published TO anon;
GRANT SELECT ON foods_published TO authenticated;

-- Add comment to the view
COMMENT ON VIEW foods_published IS 
'Deduplicated view of food products that prefers rows with kcal_per_100g when multiple sources exist for the same product. 
Ranks by: 1) presence of kcal_per_100g, 2) completeness of nutrition data, 3) recency.
Shows source_domain to indicate which data source "won" the deduplication.';

-- Add column comments for clarity
COMMENT ON COLUMN foods_published.kcal_per_100g IS 'Energy content per 100g - deduplicated to prefer sources with this data';
COMMENT ON COLUMN foods_published.protein_percent IS 'Protein percentage - from the selected (deduplicated) source';
COMMENT ON COLUMN foods_published.fat_percent IS 'Fat percentage - from the selected (deduplicated) source';
COMMENT ON COLUMN foods_published.source_domain IS 'Domain of the data source that won the deduplication (e.g., allaboutdogfood.co.uk)';
COMMENT ON COLUMN foods_published.has_complete_nutrition IS 'TRUE when kcal, protein, and fat are all available from selected source';
COMMENT ON COLUMN foods_published.quality_rating IS 'Product rating from review sites like AADF';
COMMENT ON COLUMN foods_published.brand_slug IS 'Normalized brand name for deduplication grouping';
COMMENT ON COLUMN foods_published.name_slug IS 'Normalized product name for deduplication grouping';