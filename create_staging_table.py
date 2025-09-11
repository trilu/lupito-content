#!/usr/bin/env python3
"""
Create the staging table and merge functions manually
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_KEY')
supabase = create_client(url, key)

# Create staging table using SQL
staging_sql = """
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_run_id ON foods_ingestion_staging(run_id);
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_product_key ON foods_ingestion_staging(product_key_computed);
CREATE INDEX IF NOT EXISTS idx_foods_ingestion_staging_brand_name ON foods_ingestion_staging(brand_slug, name_slug);
"""

try:
    # Execute staging table creation
    supabase.rpc('exec_sql', {'sql': staging_sql}).execute()
    print("✓ Staging table created successfully")
except Exception as e:
    print(f"Staging table creation failed: {e}")

# Test that table exists
try:
    result = supabase.table('foods_ingestion_staging').select('count').execute()
    print(f"✓ Staging table accessible")
except Exception as e:
    print(f"Staging table test failed: {e}")