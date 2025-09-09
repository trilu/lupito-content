
        CREATE OR REPLACE VIEW food_candidates_compat AS
        SELECT 
            -- Product key
            LOWER(REPLACE(TRIM(brand), ' ', '_')) || '|' || 
            LOWER(REPLACE(TRIM(product_name), ' ', '_')) || '|' || 
            COALESCE(form, 'unknown') as product_key,
            
            -- Core fields
            brand,
            LOWER(REPLACE(TRIM(brand), ' ', '_')) as brand_slug,
            product_name,
            LOWER(REPLACE(TRIM(product_name), ' ', '_')) as name_slug,
            form,
            
            -- Life stage normalization
            CASE 
                WHEN life_stage IN ('puppy', 'junior', 'growth') THEN 'puppy'
                WHEN life_stage IN ('adult', 'maintenance') THEN 'adult'
                WHEN life_stage IN ('senior', 'mature', '7+', '8+', 'aging') THEN 'senior'
                WHEN life_stage = 'all' OR life_stage LIKE '%all%stages%' THEN 'all'
                WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
                WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
                WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
                WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
                ELSE life_stage
            END as life_stage,
            
            -- Nutrition
            kcal_per_100g,
            CASE 
                WHEN kcal_per_100g IS NOT NULL THEN false
                WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN true
                ELSE false
            END as kcal_is_estimated,
            
            -- Calculate Atwater estimate if needed
            CASE 
                WHEN kcal_per_100g IS NOT NULL THEN kcal_per_100g
                WHEN protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN
                    (protein_percent * 3.5) + (fat_percent * 8.5) + 
                    ((100 - protein_percent - fat_percent - COALESCE(fiber_percent, 0) - 
                      COALESCE(ash_percent::numeric, 8) - COALESCE(moisture_percent::numeric, 10)) * 3.5)
                ELSE NULL
            END as kcal_per_100g_final,
            
            protein_percent,
            fat_percent,
            
            -- Ingredients
            ingredients_tokens,
            
            -- Derive primary protein from tokens
            CASE
                WHEN ingredients_tokens::text ~* 'chicken' THEN 'chicken'
                WHEN ingredients_tokens::text ~* 'beef' THEN 'beef'
                WHEN ingredients_tokens::text ~* 'lamb' THEN 'lamb'
                WHEN ingredients_tokens::text ~* 'salmon' THEN 'salmon'
                WHEN ingredients_tokens::text ~* 'fish' THEN 'fish'
                WHEN ingredients_tokens::text ~* 'turkey' THEN 'turkey'
                WHEN ingredients_tokens::text ~* 'duck' THEN 'duck'
                ELSE NULL
            END as primary_protein,
            
            contains_chicken as has_chicken,
            ingredients_tokens::text ~* 'poultry' as has_poultry,
            
            -- Availability
            available_countries,
            
            -- Price
            price_eur as price_per_kg,
            CASE 
                WHEN price_eur <= 3.5 THEN 'Low'
                WHEN price_eur > 3.5 AND price_eur <= 7.0 THEN 'Mid'
                WHEN price_eur > 7.0 THEN 'High'
                ELSE NULL
            END as price_bucket,
            
            -- Metadata
            image_url,
            source_url as product_url,
            'food_candidates' as source,
            last_seen_at as updated_at,
            
            -- Quality score
            (CASE WHEN life_stage IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN kcal_per_100g IS NOT NULL OR 
                      (protein_percent IS NOT NULL AND fat_percent IS NOT NULL) THEN 1 ELSE 0 END +
             CASE WHEN ingredients_tokens IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN price_eur IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1 ELSE 0 END -
             CASE WHEN kcal_per_100g IS NULL AND protein_percent IS NOT NULL AND fat_percent IS NOT NULL THEN 1 ELSE 0 END
            ) as quality_score
            
        FROM food_candidates;
        