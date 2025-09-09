
        CREATE OR REPLACE VIEW food_candidates_sc_compat AS
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
            
            -- Life stage normalization from product name
            CASE 
                WHEN product_name ~* '(senior|mature|7\+|8\+)' THEN 'senior'
                WHEN product_name ~* '(puppy|junior|growth)' THEN 'puppy'
                WHEN product_name ~* '(adult|maintenance)' THEN 'adult'
                WHEN product_name ~* 'all.?life.?stages?' THEN 'all'
                ELSE NULL
            END as life_stage,
            
            -- Nutrition (mostly null in this table)
            NULL::numeric as kcal_per_100g,
            false as kcal_is_estimated,
            NULL::numeric as kcal_per_100g_final,
            NULL::numeric as protein_percent,
            NULL::numeric as fat_percent,
            
            -- Ingredients (empty in this table)
            '[]'::jsonb as ingredients_tokens,
            NULL as primary_protein,
            false as has_chicken,
            false as has_poultry,
            
            -- Availability
            available_countries,
            
            -- Price
            NULL::numeric as price_per_kg,
            NULL as price_bucket,
            
            -- Metadata
            image_url,
            source_url as product_url,
            'food_candidates_sc' as source,
            last_seen_at as updated_at,
            
            -- Quality score (lower due to missing data)
            (CASE WHEN form IS NOT NULL THEN 1 ELSE 0 END) as quality_score
            
        FROM food_candidates_sc;
        