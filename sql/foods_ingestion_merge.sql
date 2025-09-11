-- B1A: Server-side merge function for staging → foods_canonical
-- Handles product key matching, brand allowlist checks, and safe upserts

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
    skipped_no_match INTEGER := 0;
    total_staged INTEGER;
    rec RECORD;
BEGIN
    -- Count total staged records for this run
    SELECT COUNT(*) INTO total_staged
    FROM foods_ingestion_staging
    WHERE run_id = p_run_id;

    -- Log start
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
            WHERE product_key = rec.product_key_computed
            AND (
                ingredients_raw IS NULL OR ingredients_raw = '' OR
                ingredients_tokens IS NULL OR array_length(ingredients_tokens, 1) IS NULL OR
                ingredients_language IS NULL OR ingredients_language = '' OR
                ingredients_source IS NULL OR ingredients_source = '' OR
                ingredients_parsed_at IS NULL
            );
            
            -- Check if any rows were actually updated
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
                    product_key = rec.product_key_computed,  -- Update to computed key
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
                -- No existing product found - check if brand is allowlisted
                IF EXISTS (
                    SELECT 1 FROM brand_allowlist 
                    WHERE brand_slug = rec.brand_slug 
                    AND status IN ('ACTIVE', 'PENDING')
                ) THEN
                    -- INSERT new canonical product
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
                        created_at,
                        updated_at
                    ) VALUES (
                        rec.brand,
                        SUBSTRING(rec.product_name_raw FROM 1 FOR 200),  -- Truncate if needed
                        rec.brand_slug,
                        rec.name_slug,
                        rec.product_key_computed,
                        rec.ingredients_raw,
                        rec.ingredients_tokens,
                        rec.ingredients_language,
                        rec.ingredients_source,
                        rec.ingredients_parsed_at::timestamp with time zone,
                        JSONB_BUILD_ARRAY(rec.product_url),  -- Store source URL
                        NOW(),
                        NOW()
                    );
                    
                    inserted_count := inserted_count + 1;
                    RAISE NOTICE 'Inserted new product: %', rec.product_key_computed;
                    
                ELSE
                    -- Brand not allowlisted - skip
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
    SELECT 'skipped_not_allowlisted'::TEXT, skipped_not_allowlisted, 
           FORMAT('%s products skipped (brand not allowlisted)', skipped_not_allowlisted);
    
    RETURN QUERY
    SELECT 'total_processed'::TEXT, inserted_count + updated_count, 
           FORMAT('%s total products processed successfully', inserted_count + updated_count);

    -- Final health check
    IF total_staged >= 50 AND (inserted_count + updated_count) = 0 THEN
        RAISE EXCEPTION 'HEALTH CHECK FAILED: Staged ≥50 records but processed 0. Run ID: %', p_run_id;
    END IF;

    -- Log summary
    RAISE NOTICE 'Merge completed for run_id: % | Inserted: % | Updated: % | Skipped: %', 
                 p_run_id, inserted_count, updated_count, skipped_not_allowlisted;

END;
$$ LANGUAGE plpgsql;

-- Grant execution permissions
GRANT EXECUTE ON FUNCTION merge_foods_ingestion_staging(TEXT) TO service_role;

-- Create helper function to check brand allowlist status
CREATE OR REPLACE FUNCTION check_brand_allowlist_status(p_brand_slug TEXT)
RETURNS TABLE(
    brand_slug TEXT,
    status TEXT,
    is_active BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ba.brand_slug,
        ba.status,
        ba.status IN ('ACTIVE', 'PENDING') as is_active
    FROM brand_allowlist ba
    WHERE ba.brand_slug = p_brand_slug;
    
    -- If no record found, return default
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT p_brand_slug, 'NOT_FOUND'::TEXT, FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant execution permissions
GRANT EXECUTE ON FUNCTION check_brand_allowlist_status(TEXT) TO service_role;

-- Create helper function to get staging residuals (unmerged records)
CREATE OR REPLACE FUNCTION get_staging_residuals(p_run_id TEXT)
RETURNS TABLE(
    product_key_computed TEXT,
    brand_slug TEXT,
    product_name_raw TEXT,
    reason TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH merged_keys AS (
        -- Find keys that were successfully processed
        SELECT DISTINCT s.product_key_computed
        FROM foods_ingestion_staging s
        JOIN foods_canonical c ON (
            c.product_key = s.product_key_computed OR
            (c.brand_slug = s.brand_slug AND c.name_slug = s.name_slug)
        )
        WHERE s.run_id = p_run_id
    )
    SELECT 
        s.product_key_computed,
        s.brand_slug,
        s.product_name_raw,
        CASE 
            WHEN ba.brand_slug IS NULL THEN 'Brand not in allowlist'
            WHEN ba.status NOT IN ('ACTIVE', 'PENDING') THEN FORMAT('Brand status: %s', ba.status)
            WHEN mk.product_key_computed IS NULL THEN 'No matching product found and brand not allowlisted'
            ELSE 'Unknown reason'
        END as reason
    FROM foods_ingestion_staging s
    LEFT JOIN merged_keys mk ON mk.product_key_computed = s.product_key_computed
    LEFT JOIN brand_allowlist ba ON ba.brand_slug = s.brand_slug
    WHERE s.run_id = p_run_id
    AND mk.product_key_computed IS NULL;  -- Only unmerged records
END;
$$ LANGUAGE plpgsql;

-- Grant execution permissions
GRANT EXECUTE ON FUNCTION get_staging_residuals(TEXT) TO service_role;

-- Comments for documentation
COMMENT ON FUNCTION merge_foods_ingestion_staging(TEXT) IS 'Merge staging records into foods_canonical with brand allowlist validation and conflict resolution';
COMMENT ON FUNCTION check_brand_allowlist_status(TEXT) IS 'Check if a brand is allowlisted and active for processing';
COMMENT ON FUNCTION get_staging_residuals(TEXT) IS 'Get staging records that failed to merge with reasons';