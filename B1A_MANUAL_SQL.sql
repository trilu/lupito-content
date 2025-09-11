-- B1A MANUAL SQL SETUP
-- Run this in Supabase SQL Editor to create staging infrastructure

-- 1. Create staging table for ingredient ingestion
CREATE TABLE IF NOT EXISTS foods_ingestion_staging (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    brand TEXT NOT NULL,
    brand_slug TEXT NOT NULL,
    product_name_raw TEXT NOT NULL,
    name_slug TEXT NOT NULL,
    product_key_computed TEXT NOT NULL,
    product_url TEXT,
    ingredients_raw TEXT,
    ingredients_tokens TEXT[],
    ingredients_language TEXT,
    ingredients_source TEXT,
    ingredients_parsed_at TIMESTAMP WITH TIME ZONE,
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    debug_blob JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 2. Create indexes for efficient joins
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_run_id ON foods_ingestion_staging(run_id);
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_product_key ON foods_ingestion_staging(product_key_computed);
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_brand_name ON foods_ingestion_staging(brand_slug, name_slug);

-- 3. Server-side merge function
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
                END IF;
                
            ELSE
                -- Check if brand is allowlisted (assuming table exists)
                IF EXISTS (
                    SELECT 1 FROM brand_allowlist 
                    WHERE brand_slug = rec.brand_slug 
                    AND status IN ('ACTIVE', 'PENDING')
                ) OR NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'brand_allowlist') THEN
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
                        NOW(),
                        NOW()
                    );
                    
                    inserted_count := inserted_count + 1;
                ELSE
                    skipped_not_allowlisted := skipped_not_allowlisted + 1;
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

-- 4. Helper function to check residuals
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
        'Failed to merge - check logs' as reason
    FROM foods_ingestion_staging s
    LEFT JOIN merged_keys mk ON mk.product_key_computed = s.product_key_computed
    WHERE s.run_id = p_run_id
    AND mk.product_key_computed IS NULL;
END;
$$ LANGUAGE plpgsql;