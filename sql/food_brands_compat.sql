
        CREATE OR REPLACE VIEW food_brands_compat AS
        SELECT 
            -- Product key
            LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
            LOWER(REPLACE(TRIM(name), ' ', '_')) || '|' || 
            'unknown' as product_key,
            
            -- Core fields
            brand,
            LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
            name as product_name,
            LOWER(REPLACE(TRIM(name), ' ', '_')) as name_slug,
            'unknown' as form,
            
            -- Life stage normalization
            CASE 
                WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
                WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
                WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
                WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
                WHEN life_stage = 'puppy and adult' THEN 'all'
                ELSE life_stage
            END as life_stage,
            
            -- Nutrition (not available)
            NULL::numeric as kcal_per_100g,
            false as kcal_is_estimated,
            NULL::numeric as kcal_per_100g_final,
            NULL::numeric as protein_percent,
            NULL::numeric as fat_percent,
            
            -- Ingredients (not available)
            '[]'::jsonb as ingredients_tokens,
            NULL as primary_protein,
            false as has_chicken,
            false as has_poultry,
            
            -- Availability (assume EU for legacy data)
            '["EU"]'::jsonb as available_countries,
            
            -- Price
            NULL::numeric as price_per_kg,
            NULL as price_bucket,
            
            -- Metadata
            NULL as image_url,
            NULL as product_url,
            'food_brands' as source,
            NOW() as updated_at,
            
            -- Quality score
            (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END
            ) as quality_score
            
        FROM food_brands;
        