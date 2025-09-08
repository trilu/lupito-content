#!/usr/bin/env python3
"""
Script to manage dog food brands and their official websites in Supabase.
This replaces direct AADF scraping with a workflow to:
1. Store all brands in Supabase
2. Find and add official brand websites
3. Scrape products directly from official sources
"""
import os
import json
import uuid
from datetime import datetime
from supabase import create_client, Client
from typing import List, Dict, Optional
import time

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")

supabase: Client = create_client(supabase_url, supabase_key)

# SQL to create table for brand management
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS food_brands_sc (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_name text NOT NULL UNIQUE,
    brand_normalized text, -- Normalized version for matching (lowercase, no spaces)
    
    -- Official website information
    official_website text,
    official_website_verified boolean DEFAULT false,
    website_discovery_method text, -- 'manual', 'web_search', 'aadf_reference'
    website_last_checked timestamptz,
    
    -- Scraping configuration
    scraping_status text DEFAULT 'pending', -- pending, ready, in_progress, completed, failed
    scraping_priority integer DEFAULT 0, -- Higher number = higher priority
    scraping_notes text,
    products_scraped_count integer DEFAULT 0,
    last_scraped_at timestamptz,
    
    -- Source references
    aadf_reference boolean DEFAULT false,
    aadf_url text,
    other_sources jsonb DEFAULT '[]'::jsonb,
    
    -- Metadata
    available_countries text[] DEFAULT ARRAY['UK'],
    brand_type text, -- 'manufacturer', 'private_label', 'distributor'
    parent_company text,
    
    -- Timestamps
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_food_brands_sc_brand_name ON food_brands_sc(brand_name);
CREATE INDEX IF NOT EXISTS idx_food_brands_sc_brand_normalized ON food_brands_sc(brand_normalized);
CREATE INDEX IF NOT EXISTS idx_food_brands_sc_scraping_status ON food_brands_sc(scraping_status);
CREATE INDEX IF NOT EXISTS idx_food_brands_sc_scraping_priority ON food_brands_sc(scraping_priority DESC);
CREATE INDEX IF NOT EXISTS idx_food_brands_sc_official_website ON food_brands_sc(official_website);

-- Create a separate table for products linked to brands
CREATE TABLE IF NOT EXISTS food_products_sc (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id uuid REFERENCES food_brands_sc(id) ON DELETE CASCADE,
    
    -- Product information
    product_name text NOT NULL,
    product_url text,
    form text,
    life_stage text,
    
    -- Nutritional information
    kcal_per_100g real,
    protein_percent real,
    fat_percent real,
    fiber_percent real,
    ash_percent real,
    moisture_percent real,
    
    -- Ingredients
    ingredients_raw text,
    ingredients_tokens text[],
    contains_chicken boolean DEFAULT false,
    
    -- Commercial information
    pack_sizes jsonb DEFAULT '[]'::jsonb,
    price_eur real,
    price_currency text,
    gtin text,
    image_url text,
    
    -- Metadata
    source_url text,
    fingerprint text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    -- Constraints
    UNIQUE(brand_id, product_name)
);

CREATE INDEX IF NOT EXISTS idx_food_products_sc_brand_id ON food_products_sc(brand_id);
CREATE INDEX IF NOT EXISTS idx_food_products_sc_product_name ON food_products_sc(product_name);
"""

def normalize_brand_name(brand: str) -> str:
    """Normalize brand name for matching"""
    return brand.lower().replace(' ', '').replace('-', '').replace('&', 'and').replace('.', '')

def load_aadf_brands(filename='aadf_all_brands.txt') -> List[str]:
    """Load AADF brands from text file"""
    brands = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                brands.append(line)
    return brands

def create_tables():
    """Create the food_brands_sc and food_products_sc tables"""
    print("Creating food_brands_sc and food_products_sc tables...")
    
    print("\n" + "="*80)
    print("SQL TO CREATE TABLES (execute this in Supabase SQL Editor):")
    print("="*80)
    print(CREATE_TABLE_SQL)
    print("="*80 + "\n")
    
    return True

def populate_brands():
    """Populate the table with AADF brands"""
    print("Loading AADF brands...")
    brands = load_aadf_brands()
    print(f"Found {len(brands)} brands to add")
    
    # Prepare records for insertion
    records = []
    timestamp = datetime.utcnow().isoformat()
    
    for brand in brands:
        record = {
            'id': str(uuid.uuid4()),
            'brand_name': brand,
            'brand_normalized': normalize_brand_name(brand),
            'aadf_reference': True,
            'available_countries': ['UK'],
            'scraping_status': 'pending',
            'created_at': timestamp,
            'updated_at': timestamp,
            'scraping_priority': 0,
            'products_scraped_count': 0,
            'official_website_verified': False,
            'other_sources': []
        }
        records.append(record)
    
    print(f"\nPrepared {len(records)} brand records")
    
    # Insert in batches to avoid timeouts
    batch_size = 50
    total_inserted = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            # Insert batch
            response = supabase.table('food_brands_sc').insert(batch).execute()
            total_inserted += len(batch)
            print(f"Inserted batch {i//batch_size + 1}: {len(batch)} records (Total: {total_inserted}/{len(records)})")
        except Exception as e:
            # Check if it's a duplicate key error (brand already exists)
            if 'duplicate' in str(e).lower():
                print(f"Some brands in batch {i//batch_size + 1} already exist, skipping...")
            else:
                print(f"Error inserting batch {i//batch_size + 1}: {e}")
                # Try inserting records one by one for this batch
                for record in batch:
                    try:
                        supabase.table('food_brands_sc').insert(record).execute()
                        total_inserted += 1
                    except Exception as individual_error:
                        if 'duplicate' not in str(individual_error).lower():
                            print(f"  Failed to insert brand '{record['brand_name']}': {individual_error}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: Successfully inserted {total_inserted} brand records into food_brands_sc")
    print(f"{'='*80}")
    
    # Verify insertion
    try:
        count_response = supabase.table('food_brands_sc').select('id', count='exact').execute()
        print(f"\nVerification: Table now contains {count_response.count} total records")
    except Exception as e:
        print(f"Could not verify count: {e}")

def update_brand_website(brand_name: str, website_url: str, verified: bool = False, method: str = 'manual'):
    """Update a brand's official website"""
    try:
        response = supabase.table('food_brands_sc').update({
            'official_website': website_url,
            'official_website_verified': verified,
            'website_discovery_method': method,
            'website_last_checked': datetime.utcnow().isoformat(),
            'scraping_status': 'ready' if website_url else 'pending',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('brand_name', brand_name).execute()
        
        if response.data:
            print(f"✓ Updated website for {brand_name}: {website_url}")
            return True
        else:
            print(f"✗ Brand '{brand_name}' not found")
            return False
    except Exception as e:
        print(f"Error updating brand website: {e}")
        return False

def get_brands_without_websites(limit: int = 10) -> List[Dict]:
    """Get brands that don't have official websites yet"""
    try:
        response = supabase.table('food_brands_sc').select('*').is_('official_website', 'null').order('scraping_priority', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching brands without websites: {e}")
        return []

def get_ready_for_scraping(limit: int = 5) -> List[Dict]:
    """Get brands ready for scraping (have websites, status is 'ready')"""
    try:
        response = supabase.table('food_brands_sc').select('*').eq('scraping_status', 'ready').not_.is_('official_website', 'null').order('scraping_priority', desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching brands ready for scraping: {e}")
        return []

def mark_scraping_started(brand_id: str):
    """Mark a brand as being scraped"""
    try:
        supabase.table('food_brands_sc').update({
            'scraping_status': 'in_progress',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', brand_id).execute()
    except Exception as e:
        print(f"Error marking scraping started: {e}")

def mark_scraping_completed(brand_id: str, products_count: int):
    """Mark a brand as successfully scraped"""
    try:
        supabase.table('food_brands_sc').update({
            'scraping_status': 'completed',
            'products_scraped_count': products_count,
            'last_scraped_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', brand_id).execute()
    except Exception as e:
        print(f"Error marking scraping completed: {e}")

def mark_scraping_failed(brand_id: str, error_notes: str):
    """Mark a brand as failed to scrape"""
    try:
        supabase.table('food_brands_sc').update({
            'scraping_status': 'failed',
            'scraping_notes': error_notes,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', brand_id).execute()
    except Exception as e:
        print(f"Error marking scraping failed: {e}")

def display_statistics():
    """Display current statistics about brands"""
    try:
        # Total brands
        total = supabase.table('food_brands_sc').select('id', count='exact').execute()
        print(f"\nTotal brands: {total.count}")
        
        # Brands with websites
        with_websites = supabase.table('food_brands_sc').select('id', count='exact').not_.is_('official_website', 'null').execute()
        print(f"Brands with websites: {with_websites.count}")
        
        # Brands by scraping status
        statuses = ['pending', 'ready', 'in_progress', 'completed', 'failed']
        print("\nScraping status breakdown:")
        for status in statuses:
            count = supabase.table('food_brands_sc').select('id', count='exact').eq('scraping_status', status).execute()
            print(f"  {status}: {count.count}")
        
        # Total products scraped
        products_count = supabase.table('food_products_sc').select('id', count='exact').execute()
        print(f"\nTotal products scraped: {products_count.count}")
        
    except Exception as e:
        print(f"Error displaying statistics: {e}")

def main():
    print("="*80)
    print("BRAND WEBSITE MANAGEMENT SYSTEM")
    print("="*80)
    
    # Step 1: Create tables (prints SQL for manual execution)
    create_tables()
    
    # Step 2: Check if table exists before populating
    print("\nChecking if food_brands_sc table exists...")
    try:
        # Try to query the table
        test_response = supabase.table('food_brands_sc').select('id').limit(1).execute()
        print("✓ Table exists")
        
        # Check if we need to populate
        count_response = supabase.table('food_brands_sc').select('id', count='exact').execute()
        if count_response.count == 0:
            print("Table is empty, populating with brands...")
            populate_brands()
        else:
            print(f"Table already contains {count_response.count} brands")
        
        # Display statistics
        display_statistics()
        
        # Show example workflow
        print("\n" + "="*80)
        print("WORKFLOW:")
        print("="*80)
        print("1. Run this script to populate brands")
        print("2. Use update_brand_website() to add official websites")
        print("3. Use get_brands_without_websites() to find brands needing research")
        print("4. Use get_ready_for_scraping() to get brands ready to scrape")
        print("5. Scrape products from official websites")
        print("6. Store products in food_products_sc table linked to brands")
        print("="*80)
        
    except Exception as e:
        if 'relation' in str(e).lower() and 'does not exist' in str(e).lower():
            print("\n" + "!"*80)
            print("WARNING: Table food_brands_sc does not exist!")
            print("Please execute the SQL above in Supabase SQL Editor first.")
            print("Then run this script again to populate the brands.")
            print("!"*80)
        else:
            print(f"Error checking table: {e}")
            print("\nIf the table doesn't exist, please create it using the SQL above.")

if __name__ == "__main__":
    main()