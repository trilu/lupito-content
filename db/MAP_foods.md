# Food Products Database Mapping Documentation

## Overview
This document defines the canonical schema for the AI service and provides mappings from existing database tables to this unified structure.

Generated: 2025-01-07

## 1. Current Database Tables

### 1.1 food_candidates Table
Primary table for scraped and normalized food products.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| source_domain | text | NO | Website domain (e.g., petfoodexpert.com) |
| source_url | text | NO | Original product URL |
| brand | text | YES | Product brand name |
| product_name | text | YES | Product name |
| form | text | YES | Product form (dry/wet/raw) |
| life_stage | text | YES | Target life stage |
| kcal_per_100g | numeric | YES | Energy content |
| protein_percent | numeric | YES | Protein percentage |
| fat_percent | numeric | YES | Fat percentage |
| fiber_percent | numeric | YES | Fiber percentage |
| ash_percent | numeric | YES | Ash percentage |
| moisture_percent | numeric | YES | Moisture percentage |
| ingredients_raw | text | YES | Raw ingredients text |
| ingredients_tokens | text[] | YES | Tokenized ingredients array |
| contains_chicken | boolean | YES | Chicken presence flag |
| pack_sizes | text[] | YES | Available package sizes |
| price_eur | numeric | YES | Price in EUR |
| price_currency | text | YES | Original price currency |
| available_countries | text[] | YES | Country availability |
| gtin | text | YES | Global Trade Item Number |
| image_url | text | YES | Product image URL |
| kcal_basis | text | YES | Basis for kcal calculation |
| fingerprint | text | YES | Unique product fingerprint |
| first_seen_at | timestamptz | YES | First discovery date |
| last_seen_at | timestamptz | YES | Last update date |

### 1.2 food_brands Table
Brand information table (limited usage).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | uuid | NO | Primary key |
| brand_name | text | YES | Brand name |
| product_name | text | YES | Product name |
| product_type | text | YES | Type of product |
| life_stage | text | YES | Target life stage |
| protein_percent | integer | YES | Protein percentage |
| fat_percent | integer | YES | Fat percentage |
| fiber_percent | numeric | YES | Fiber percentage |
| main_ingredients | text[] | YES | Main ingredients list |
| packaging_sizes | text[] | YES | Available sizes |
| manufacturer | text | YES | Manufacturer name |
| country_of_origin | text | YES | Origin country |
| tags | text[] | YES | Product tags |
| created_at | timestamptz | YES | Creation timestamp |

### 1.3 foods_published View
Published view combining data from food_candidates with derived fields.

| Column | Type | Description |
|--------|------|-------------|
| All columns from food_candidates | - | Inherited |
| price_bucket | text | Derived: low/mid/high based on price_eur |
| has_complete_nutrition | boolean | Flag for nutrition completeness |
| nutrition_note | text | Additional nutrition notes |

### 1.4 food_raw Table
Raw HTML and JSON storage.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| source_domain | text | Website domain |
| source_url | text | Original URL |
| html_gcs_path | text | GCS path to HTML |
| parsed_json | jsonb | Parsed JSON data |
| raw_type | text | Type of raw data |
| fingerprint | text | Content fingerprint |
| first_seen_at | timestamptz | First seen date |
| last_seen_at | timestamptz | Last update date |

## 2. Canonical Schema for AI Service

The AI service requires a unified schema with normalized fields for consistent querying and recommendations.

### Required Canonical Fields

```sql
CREATE TABLE canonical_foods (
    -- Identity
    id UUID PRIMARY KEY,
    brand TEXT NOT NULL,
    name TEXT NOT NULL,
    
    -- Product characteristics
    form TEXT NOT NULL,          -- Normalized: dry|wet|freeze_dried|raw|any
    life_stage TEXT NOT NULL,    -- Normalized: puppy|adult|senior|all
    
    -- Ingredients
    ingredients_tokens TEXT[] NOT NULL DEFAULT '{}',
    contains_chicken BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Nutrition (per 100g)
    kcal_per_100g NUMERIC,
    protein_percent NUMERIC,
    fat_percent NUMERIC,
    
    -- Pricing
    price_per_kg NUMERIC,
    price_bucket TEXT NOT NULL,  -- Normalized: low|mid|high
    
    -- Availability
    available_countries TEXT[] NOT NULL DEFAULT '{EU}',
    
    -- Media
    image_public_url TEXT,
    
    -- Metadata
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    source_domain TEXT NOT NULL
);
```

### Field Specifications

| Field | Type | Required | Values | Default | Description |
|-------|------|----------|--------|---------|-------------|
| id | UUID | YES | - | - | Unique identifier |
| brand | TEXT | YES | - | - | Brand name, cleaned |
| name | TEXT | YES | - | - | Product name, cleaned |
| form | TEXT | YES | dry, wet, freeze_dried, raw, any | any | Product physical form |
| life_stage | TEXT | YES | puppy, adult, senior, all | all | Target age group |
| ingredients_tokens | TEXT[] | YES | - | {} | Tokenized ingredients |
| contains_chicken | BOOLEAN | YES | true, false | false | Chicken/poultry presence |
| kcal_per_100g | NUMERIC | NO | > 0 | NULL | Energy density |
| protein_percent | NUMERIC | NO | 0-100 | NULL | Protein content |
| fat_percent | NUMERIC | NO | 0-100 | NULL | Fat content |
| price_per_kg | NUMERIC | NO | > 0 | NULL | Price per kilogram |
| price_bucket | TEXT | YES | low, mid, high | mid | Price category |
| available_countries | TEXT[] | YES | - | {EU} | Country codes |
| image_public_url | TEXT | NO | - | NULL | Public image URL |
| first_seen_at | TIMESTAMPTZ | YES | - | NOW() | First discovery |
| last_seen_at | TIMESTAMPTZ | YES | - | NOW() | Last update |
| source_domain | TEXT | YES | - | - | Source website |

## 3. Mapping Tables

### 3.1 food_candidates → Canonical Mapping

| Canonical Field | Source Field | Transformation |
|-----------------|--------------|----------------|
| id | id | Direct copy |
| brand | brand | TRIM, proper case |
| name | product_name | TRIM, proper case |
| form | form | Normalize: COALESCE(form, derive_form(ingredients_raw), 'any') |
| life_stage | life_stage | Normalize: COALESCE(life_stage, derive_life_stage(ingredients_raw), 'all') |
| ingredients_tokens | ingredients_tokens | COALESCE(ingredients_tokens, tokenize(ingredients_raw), '{}') |
| contains_chicken | contains_chicken | COALESCE(contains_chicken, check_tokens(ingredients_tokens), FALSE) |
| kcal_per_100g | kcal_per_100g | Direct copy |
| protein_percent | protein_percent | Direct copy |
| fat_percent | fat_percent | Direct copy |
| price_per_kg | - | Calculate: price_eur * (1000 / avg_pack_size_g) |
| price_bucket | - | Derive: CASE WHEN price_eur < 3 THEN 'low' WHEN < 6 THEN 'mid' ELSE 'high' |
| available_countries | available_countries | COALESCE(available_countries, '{EU}') |
| image_public_url | image_url | Direct copy |
| first_seen_at | first_seen_at | Direct copy |
| last_seen_at | last_seen_at | Direct copy |
| source_domain | source_domain | Direct copy |

### 3.2 food_brands → Canonical Mapping

| Canonical Field | Source Field | Transformation |
|-----------------|--------------|----------------|
| id | id | Direct copy |
| brand | brand_name | TRIM, proper case |
| name | product_name | TRIM, proper case |
| form | product_type | Map: derive_form(product_type, 'any') |
| life_stage | life_stage | Normalize: COALESCE(life_stage, 'all') |
| ingredients_tokens | main_ingredients | Direct copy if array, else tokenize |
| contains_chicken | - | Derive: check_ingredients(main_ingredients, 'chicken') |
| kcal_per_100g | - | NULL (not available) |
| protein_percent | protein_percent | Cast to NUMERIC |
| fat_percent | fat_percent | Cast to NUMERIC |
| price_per_kg | - | NULL (not available) |
| price_bucket | - | Default: 'mid' |
| available_countries | - | Derive: map_country(country_of_origin, '{EU}') |
| image_public_url | - | NULL (not available) |
| first_seen_at | created_at | Direct copy |
| last_seen_at | created_at | Direct copy |
| source_domain | - | Constant: 'internal' |

### 3.3 foods_published → Canonical Mapping

| Canonical Field | Source Field | Transformation |
|-----------------|--------------|----------------|
| id | id | Direct copy |
| brand | brand | Direct copy |
| name | product_name | Direct copy |
| form | form | COALESCE(form, 'any') |
| life_stage | life_stage | COALESCE(life_stage, 'all') |
| ingredients_tokens | ingredients_tokens | Direct copy |
| contains_chicken | contains_chicken | Direct copy |
| kcal_per_100g | kcal_per_100g | Direct copy |
| protein_percent | protein_percent | Direct copy |
| fat_percent | fat_percent | Direct copy |
| price_per_kg | - | Calculate from price_eur |
| price_bucket | price_bucket | Direct copy |
| available_countries | available_countries | Direct copy |
| image_public_url | - | Build from image_url |
| first_seen_at | first_seen_at | Direct copy |
| last_seen_at | last_seen_at | Direct copy |
| source_domain | source_domain | Direct copy |

## 4. Transformation Functions

### 4.1 Form Normalization
```sql
CREATE FUNCTION normalize_form(input TEXT) RETURNS TEXT AS $$
BEGIN
    RETURN CASE 
        WHEN LOWER(input) LIKE '%dry%' THEN 'dry'
        WHEN LOWER(input) LIKE '%wet%' OR LOWER(input) LIKE '%can%' OR LOWER(input) LIKE '%pouch%' THEN 'wet'
        WHEN LOWER(input) LIKE '%freeze%' OR LOWER(input) LIKE '%dried%' THEN 'freeze_dried'
        WHEN LOWER(input) LIKE '%raw%' OR LOWER(input) LIKE '%frozen%' THEN 'raw'
        ELSE 'any'
    END;
END;
$$ LANGUAGE plpgsql;
```

### 4.2 Life Stage Normalization
```sql
CREATE FUNCTION normalize_life_stage(input TEXT) RETURNS TEXT AS $$
BEGIN
    RETURN CASE 
        WHEN LOWER(input) LIKE '%puppy%' OR LOWER(input) LIKE '%junior%' THEN 'puppy'
        WHEN LOWER(input) LIKE '%adult%' THEN 'adult'
        WHEN LOWER(input) LIKE '%senior%' OR LOWER(input) LIKE '%mature%' THEN 'senior'
        WHEN LOWER(input) LIKE '%all%' OR input IS NULL THEN 'all'
        ELSE 'all'
    END;
END;
$$ LANGUAGE plpgsql;
```

### 4.3 Ingredient Tokenization
```sql
CREATE FUNCTION tokenize_ingredients(raw_text TEXT) RETURNS TEXT[] AS $$
BEGIN
    IF raw_text IS NULL THEN
        RETURN '{}';
    END IF;
    
    -- Split by common separators and clean
    RETURN string_to_array(
        LOWER(
            regexp_replace(raw_text, '[,;()]', ' ', 'g')
        ), 
        ' '
    );
END;
$$ LANGUAGE plpgsql;
```

### 4.4 Chicken Detection
```sql
CREATE FUNCTION contains_chicken_check(tokens TEXT[]) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 
        FROM unnest(tokens) AS token
        WHERE token ILIKE '%chicken%' 
           OR token ILIKE '%poultry%'
           OR token ILIKE '%fowl%'
    );
END;
$$ LANGUAGE plpgsql;
```

### 4.5 Price Bucket Derivation
```sql
CREATE FUNCTION derive_price_bucket(price_eur NUMERIC) RETURNS TEXT AS $$
BEGIN
    RETURN CASE
        WHEN price_eur IS NULL THEN 'mid'
        WHEN price_eur < 3 THEN 'low'
        WHEN price_eur < 6 THEN 'mid'
        ELSE 'high'
    END;
END;
$$ LANGUAGE plpgsql;
```

## 5. Implementation SQL

### Create Canonical View
```sql
CREATE OR REPLACE VIEW canonical_foods_view AS
SELECT 
    -- Identity
    id,
    TRIM(brand) as brand,
    TRIM(product_name) as name,
    
    -- Product characteristics
    COALESCE(
        normalize_form(form),
        normalize_form(ingredients_raw),
        'any'
    ) as form,
    
    COALESCE(
        normalize_life_stage(life_stage),
        normalize_life_stage(ingredients_raw),
        'all'
    ) as life_stage,
    
    -- Ingredients
    COALESCE(
        ingredients_tokens,
        tokenize_ingredients(ingredients_raw),
        '{}'::TEXT[]
    ) as ingredients_tokens,
    
    COALESCE(
        contains_chicken,
        contains_chicken_check(ingredients_tokens),
        FALSE
    ) as contains_chicken,
    
    -- Nutrition
    kcal_per_100g,
    protein_percent,
    fat_percent,
    
    -- Pricing
    CASE 
        WHEN price_eur IS NOT NULL AND pack_sizes IS NOT NULL THEN
            price_eur * 1000.0 / COALESCE(
                (SELECT AVG(CAST(regexp_replace(size, '[^0-9]', '', 'g') AS NUMERIC))
                 FROM unnest(pack_sizes) AS size
                 WHERE size ~ '[0-9]'),
                1000.0
            )
        ELSE NULL
    END as price_per_kg,
    
    derive_price_bucket(price_eur) as price_bucket,
    
    -- Availability
    COALESCE(available_countries, '{EU}'::TEXT[]) as available_countries,
    
    -- Media
    image_url as image_public_url,
    
    -- Metadata
    first_seen_at,
    last_seen_at,
    source_domain
    
FROM food_candidates
WHERE brand IS NOT NULL 
  AND product_name IS NOT NULL;
```

## 6. Data Quality Notes

### Current Issues
1. **Missing nutrition data**: Many products lack complete nutritional information
2. **Inconsistent forms**: Product forms not always populated, requiring derivation
3. **Price data gaps**: Limited price information available
4. **Single source**: Currently only petfoodexpert.com data

### Recommended Improvements
1. Implement nutrition estimation models for missing data
2. Add form detection from product names and descriptions
3. Integrate multiple price sources for better coverage
4. Expand to additional pet food websites
5. Add breed-specific and health condition tags
6. Implement allergen detection beyond chicken

## 7. Usage Examples

### Query Canonical View
```sql
-- Get all dry adult dog foods with chicken under €5/kg
SELECT brand, name, protein_percent, price_per_kg
FROM canonical_foods_view
WHERE form = 'dry'
  AND life_stage = 'adult'
  AND contains_chicken = TRUE
  AND price_per_kg < 5
ORDER BY protein_percent DESC;

-- Find high-protein puppy foods
SELECT brand, name, protein_percent, form
FROM canonical_foods_view
WHERE life_stage = 'puppy'
  AND protein_percent > 30
ORDER BY protein_percent DESC;
```

### Update Canonical Data
```sql
-- Refresh materialized view (if created)
REFRESH MATERIALIZED VIEW CONCURRENTLY canonical_foods_materialized;

-- Update missing forms
UPDATE food_candidates
SET form = normalize_form(product_name || ' ' || COALESCE(ingredients_raw, ''))
WHERE form IS NULL;
```

## 8. Maintenance

### Regular Tasks
- **Daily**: Check for new products without canonical mappings
- **Weekly**: Update derived fields (price_bucket, contains_chicken)
- **Monthly**: Review and update normalization functions
- **Quarterly**: Audit data quality and completeness

### Monitoring Queries
```sql
-- Check mapping coverage
SELECT 
    COUNT(*) as total_products,
    COUNT(form) as has_form,
    COUNT(life_stage) as has_life_stage,
    COUNT(ingredients_tokens) as has_ingredients,
    COUNT(image_url) as has_images,
    COUNT(price_eur) as has_prices
FROM food_candidates;

-- Find unmapped products
SELECT brand, product_name, source_url
FROM food_candidates
WHERE form IS NULL 
   OR life_stage IS NULL
   OR ingredients_tokens IS NULL OR ingredients_tokens = '{}'
LIMIT 10;
```

---

*Generated automatically by analyzing lupito-content database schema*
*Last updated: 2025-01-07*