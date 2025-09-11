#!/usr/bin/env python3
"""
Setup B1A schema using psycopg2 direct connection
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection from Supabase connection string
db_url = os.getenv('DATABASE_URL')  # Should be in format: postgresql://user:pass@host:port/db

if not db_url:
    print("DATABASE_URL not found in .env")
    print("Please add your Supabase PostgreSQL connection string to .env as:")
    print("DATABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Create staging table
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
    
    cur.execute(staging_sql)
    conn.commit()
    print("✓ Staging table created successfully")
    
    # Test table exists
    cur.execute("SELECT COUNT(*) FROM foods_ingestion_staging")
    count = cur.fetchone()[0]
    print(f"✓ Staging table accessible (current records: {count})")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Database setup failed: {e}")
    print("Note: You may need to run this manually in Supabase SQL Editor")