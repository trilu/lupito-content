-- Lupito Content Ingestion Schema
-- Tables for storing raw scraped data and parsed food products

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for storing raw HTML snapshots and metadata
CREATE TABLE IF NOT EXISTS food_raw (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_domain TEXT NOT NULL,
  source_url TEXT UNIQUE NOT NULL,
  html_gcs_path TEXT,
  parsed_json JSONB,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ DEFAULT NOW(),
  fingerprint TEXT  -- hash of (brand+name+ingredients) to detect updates
);

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_food_raw_source_url ON food_raw(source_url);
CREATE INDEX IF NOT EXISTS idx_food_raw_fingerprint ON food_raw(fingerprint);

-- Table for parsed and normalized food product data
CREATE TABLE IF NOT EXISTS food_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_domain TEXT NOT NULL,
  source_url TEXT NOT NULL,
  brand TEXT,
  product_name TEXT,
  form TEXT, -- dry/wet/raw/vet
  life_stage TEXT, -- puppy/adult/senior/all
  kcal_per_100g NUMERIC,
  protein_percent NUMERIC,
  fat_percent NUMERIC,
  fiber_percent NUMERIC,
  ash_percent NUMERIC,
  moisture_percent NUMERIC,
  ingredients_raw TEXT,
  ingredients_tokens TEXT[] DEFAULT '{}',
  contains_chicken BOOLEAN DEFAULT FALSE,
  pack_sizes TEXT[] DEFAULT '{}',
  price_eur NUMERIC,
  price_currency TEXT,
  available_countries TEXT[] DEFAULT '{EU}',
  gtin TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at TIMESTAMPTZ DEFAULT NOW(),
  fingerprint TEXT
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_food_candidates_brand ON food_candidates(brand);
CREATE INDEX IF NOT EXISTS idx_food_candidates_form ON food_candidates(form);
CREATE INDEX IF NOT EXISTS idx_food_candidates_life_stage ON food_candidates(life_stage);
CREATE INDEX IF NOT EXISTS idx_food_candidates_fingerprint ON food_candidates(fingerprint);

-- View for published foods with normalized fields for the AI service
CREATE OR REPLACE VIEW foods_published AS
SELECT 
  id,
  source_domain,
  source_url,
  brand,
  product_name,
  form,
  life_stage,
  kcal_per_100g,
  protein_percent,
  fat_percent,
  fiber_percent,
  ash_percent,
  moisture_percent,
  ingredients_raw,
  -- Ensure tokens are trimmed and lowercased
  ARRAY(
    SELECT DISTINCT LOWER(TRIM(token))
    FROM UNNEST(ingredients_tokens) AS token
    WHERE TRIM(token) != ''
  ) AS ingredients_tokens,
  -- Ensure contains_chicken is set based on tokens
  CASE 
    WHEN contains_chicken = TRUE THEN TRUE
    WHEN EXISTS (
      SELECT 1 
      FROM UNNEST(ingredients_tokens) AS token 
      WHERE LOWER(token) IN ('chicken', 'chicken fat', 'chicken meal', 'chicken liver')
    ) THEN TRUE
    ELSE FALSE
  END AS contains_chicken,
  pack_sizes,
  price_eur,
  -- Derive price bucket based on price_eur
  CASE
    WHEN price_eur IS NULL THEN 'mid'
    WHEN price_eur < 3 THEN 'low'
    WHEN price_eur < 6 THEN 'mid'
    ELSE 'high'
  END AS price_bucket,
  -- Ensure available_countries defaults to EU
  COALESCE(available_countries, '{EU}') AS available_countries,
  gtin,
  first_seen_at,
  last_seen_at
FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;

-- Grant appropriate permissions (adjust as needed for your Supabase setup)
-- GRANT SELECT ON foods_published TO anon;
-- GRANT SELECT ON foods_published TO authenticated;