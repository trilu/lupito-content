-- B1A MERGE FUNCTION FIX
-- Corrected to match actual foods_canonical schema (no created_at column)

CREATE OR REPLACE FUNCTION merge_foods_ingestion_staging(p_run_id TEXT)
RETURNS TABLE(
    result_type TEXT,
    count INTEGER,
    details TEXT
) AS $$
DECLARE
    inserted_count INTEGER := 0;
    updated_count INTEGER := 0;
    skipped_not_allowlisted INTEGER := 0;
    total_staged INTEGER;
    rec RECORD;
BEGIN
    -- Count total staged records
    SELECT COUNT(*) INTO total_staged
    FROM foods_ingestion_staging
    WHERE run_id = p_run_id;

    RAISE NOTICE 'Starting merge for run_id: % with % staged records', p_run_id, total_staged;

    -- Process each staging record
    FOR rec IN 
        SELECT * FROM foods_ingestion_staging 
        WHERE run_id = p_run_id
        ORDER BY brand, product_name_raw
    LOOP
        -- Try to find existing product by product_key first
        IF EXISTS (
            SELECT 1 FROM foods_canonical 
            WHERE product_key = rec.product_key_computed
        ) THEN
            -- UPDATE existing product (only null/empty fields)
            UPDATE foods_canonical 
            SET 
                ingredients_raw = COALESCE(NULLIF(ingredients_raw, ''), rec.ingredients_raw),
                ingredients_tokens = CASE 
                    WHEN ingredients_tokens IS NULL OR array_length(ingredients_tokens, 1) IS NULL 
                    THEN rec.ingredients_tokens 
                    ELSE ingredients_tokens 
                END,
                ingredients_language = COALESCE(NULLIF(ingredients_language, ''), rec.ingredients_language),
                ingredients_source = COALESCE(NULLIF(ingredients_source, ''), rec.ingredients_source),
                ingredients_parsed_at = COALESCE(ingredients_parsed_at, rec.ingredients_parsed_at::timestamp with time zone),
                updated_at = NOW()
            WHERE product_key = rec.product_key_computed;
            
            IF FOUND THEN
                updated_count := updated_count + 1;
                RAISE NOTICE 'Updated existing product: %', rec.product_key_computed;
            END IF;
            
        ELSE
            -- Try fallback match by (brand_slug, name_slug)
            IF EXISTS (
                SELECT 1 FROM foods_canonical 
                WHERE brand_slug = rec.brand_slug 
                AND name_slug = rec.name_slug
            ) THEN
                -- UPDATE by brand+name match
                UPDATE foods_canonical 
                SET 
                    product_key = rec.product_key_computed,
                    ingredients_raw = COALESCE(NULLIF(ingredients_raw, ''), rec.ingredients_raw),
                    ingredients_tokens = CASE 
                        WHEN ingredients_tokens IS NULL OR array_length(ingredients_tokens, 1) IS NULL 
                        THEN rec.ingredients_tokens 
                        ELSE ingredients_tokens 
                    END,
                    ingredients_language = COALESCE(NULLIF(ingredients_language, ''), rec.ingredients_language),
                    ingredients_source = COALESCE(NULLIF(ingredients_source, ''), rec.ingredients_source),
                    ingredients_parsed_at = COALESCE(ingredients_parsed_at, rec.ingredients_parsed_at::timestamp with time zone),
                    updated_at = NOW()
                WHERE brand_slug = rec.brand_slug 
                AND name_slug = rec.name_slug;
                
                IF FOUND THEN
                    updated_count := updated_count + 1;
                    RAISE NOTICE 'Updated by brand+name match: % -> %', rec.name_slug, rec.product_key_computed;
                END IF;
                
            ELSE
                -- Check if brand is allowlisted (assuming table exists)
                IF EXISTS (
                    SELECT 1 FROM brand_allowlist 
                    WHERE brand_slug = rec.brand_slug 
                    AND status IN ('ACTIVE', 'PENDING')
                ) OR NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'brand_allowlist') THEN
                    -- INSERT new canonical product (removed created_at, using only existing columns)
                    INSERT INTO foods_canonical (
                        brand,
                        product_name,
                        brand_slug,
                        name_slug,
                        product_key,
                        ingredients_raw,
                        ingredients_tokens,
                        ingredients_language,
                        ingredients_source,
                        ingredients_parsed_at,
                        sources,
                        updated_at
                    ) VALUES (
                        rec.brand,
                        SUBSTRING(rec.product_name_raw FROM 1 FOR 200),
                        rec.brand_slug,
                        rec.name_slug,
                        rec.product_key_computed,
                        rec.ingredients_raw,
                        rec.ingredients_tokens,
                        rec.ingredients_language,
                        rec.ingredients_source,
                        rec.ingredients_parsed_at::timestamp with time zone,
                        CASE WHEN rec.product_url IS NOT NULL THEN JSONB_BUILD_ARRAY(rec.product_url) ELSE NULL END,
                        NOW()
                    );
                    
                    inserted_count := inserted_count + 1;
                    RAISE NOTICE 'Inserted new product: %', rec.product_key_computed;
                ELSE
                    skipped_not_allowlisted := skipped_not_allowlisted + 1;
                    RAISE NOTICE 'Skipped (brand not allowlisted): %', rec.brand_slug;
                END IF;
            END IF;
        END IF;
    END LOOP;

    -- Return summary results
    RETURN QUERY
    SELECT 'inserted'::TEXT, inserted_count, FORMAT('%s new products created', inserted_count);
    
    RETURN QUERY
    SELECT 'updated'::TEXT, updated_count, FORMAT('%s existing products updated', updated_count);
    
    RETURN QUERY
    SELECT 'skipped'::TEXT, skipped_not_allowlisted, 
           FORMAT('%s products skipped (brand restrictions)', skipped_not_allowlisted);

    -- Health check
    IF total_staged >= 50 AND (inserted_count + updated_count) = 0 THEN
        RAISE EXCEPTION 'HEALTH CHECK FAILED: Staged % records but processed 0. Run ID: %', total_staged, p_run_id;
    END IF;

    RAISE NOTICE 'Merge completed for run_id: % | Inserted: % | Updated: % | Skipped: %', 
                 p_run_id, inserted_count, updated_count, skipped_not_allowlisted;

END;
$$ LANGUAGE plpgsql;