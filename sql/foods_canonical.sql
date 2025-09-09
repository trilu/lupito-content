
        -- Drop and recreate foods_canonical table
        DROP TABLE IF EXISTS foods_canonical CASCADE;
        
        CREATE TABLE foods_canonical AS
        WITH ranked_products AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY product_key
                    ORDER BY 
                        -- 1. kcal known > estimated > null
                        CASE 
                            WHEN kcal_per_100g_final IS NOT NULL AND NOT kcal_is_estimated THEN 1
                            WHEN kcal_per_100g_final IS NOT NULL AND kcal_is_estimated THEN 2
                            ELSE 3
                        END,
                        -- 2. specific life_stage > all > null
                        CASE 
                            WHEN life_stage IN ('puppy', 'adult', 'senior') THEN 1
                            WHEN life_stage = 'all' THEN 2
                            ELSE 3
                        END,
                        -- 3. richer ingredients (more tokens)
                        CASE 
                            WHEN ingredients_tokens IS NOT NULL THEN 
                                jsonb_array_length(ingredients_tokens)
                            ELSE 0
                        END DESC,
                        -- 4. price present > missing
                        CASE WHEN price_per_kg IS NOT NULL THEN 1 ELSE 2 END,
                        -- 5. higher quality score
                        quality_score DESC,
                        -- 6. newest updated_at
                        updated_at DESC NULLS LAST
                ) as rank,
                
                -- Track sources for provenance
                jsonb_build_object(
                    'source', source,
                    'updated_at', updated_at
                ) as source_info
            FROM foods_union_all
        ),
        aggregated_sources AS (
            SELECT 
                product_key,
                jsonb_agg(source_info ORDER BY rank) as sources
            FROM ranked_products
            GROUP BY product_key
        )
        SELECT 
            r.*,
            a.sources
        FROM ranked_products r
        JOIN aggregated_sources a ON r.product_key = a.product_key
        WHERE r.rank = 1;
        
        -- Add indexes
        CREATE UNIQUE INDEX idx_foods_canonical_product_key ON foods_canonical(product_key);
        CREATE INDEX idx_foods_canonical_brand_slug ON foods_canonical(brand_slug);
        CREATE INDEX idx_foods_canonical_life_stage ON foods_canonical(life_stage);
        CREATE INDEX idx_foods_canonical_form ON foods_canonical(form);
        