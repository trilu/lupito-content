
        -- Create foods_published view for AI consumption
        CREATE OR REPLACE VIEW foods_published AS
        SELECT 
            product_key,
            brand,
            brand_slug,
            product_name,
            name_slug,
            form,
            life_stage,
            kcal_per_100g_final as kcal_per_100g,
            kcal_is_estimated,
            protein_percent,
            fat_percent,
            ingredients_tokens,
            primary_protein,
            has_chicken,
            has_poultry,
            available_countries,
            price_per_kg,
            price_bucket,
            image_url,
            product_url,
            source,
            updated_at,
            quality_score,
            sources
        FROM foods_canonical;
        
        -- Create GIN indexes for array/jsonb columns
        CREATE INDEX IF NOT EXISTS idx_foods_canonical_countries_gin 
        ON foods_canonical USING GIN (available_countries);
        
        CREATE INDEX IF NOT EXISTS idx_foods_canonical_tokens_gin 
        ON foods_canonical USING GIN (ingredients_tokens);
        