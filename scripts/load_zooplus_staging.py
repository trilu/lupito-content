#!/usr/bin/env python3
"""
Load deduplicated Zooplus data into staging table
"""

import pandas as pd
import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def prepare_data_for_staging(row):
    """Prepare a row for insertion into staging table"""
    # Extract base URL
    base_url = row['product_url']
    if '?activeVariant=' in base_url:
        base_url = base_url.split('?activeVariant=')[0]
    
    return {
        'product_key': row['product_key'],
        'brand': row['brand'],
        'product_name': row['product_name'],
        'product_url': row['product_url'],
        'base_url': base_url,
        'food_type': row.get('food_type', 'unknown'),
        'has_ingredients': bool(row.get('has_ingredients', False)),
        'ingredients_preview': row.get('ingredients_preview', '') if row.get('has_ingredients') else None,
        'source_file': row.get('source_file', ''),
        'is_variant': False,  # These are already deduplicated
        'variant_of_url': None,
        'processed': False,
        'matched_product_key': None,
        'match_type': None,
        'match_confidence': None
    }

def main():
    print("📦 LOADING ZOOPLUS DATA INTO STAGING TABLE")
    print("=" * 60)
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Load deduplicated data
    print("Loading deduplicated data...")
    df = pd.read_csv('data/zooplus_deduped.csv')
    print(f"  Found {len(df)} unique products to load")
    
    # Check current staging table
    existing = supabase.table('zooplus_staging').select('count', count='exact').execute()
    if existing.count > 0:
        print(f"  ⚠️  Staging table already has {existing.count} records")
        response = input("  Clear existing data? (y/n): ")
        if response.lower() == 'y':
            supabase.table('zooplus_staging').delete().neq('id', 0).execute()
            print("  ✅ Cleared existing data")
    
    # Prepare data for insertion
    print("\nPreparing data for insertion...")
    records = []
    for _, row in df.iterrows():
        records.append(prepare_data_for_staging(row))
    
    # Insert in batches
    batch_size = 100
    total_batches = (len(records) + batch_size - 1) // batch_size
    
    print(f"\nInserting {len(records)} records in {total_batches} batches...")
    
    success_count = 0
    error_count = 0
    errors = []
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        try:
            result = supabase.table('zooplus_staging').insert(batch).execute()
            success_count += len(batch)
            print(f"  Batch {batch_num}/{total_batches}: ✅ {len(batch)} records inserted")
        except Exception as e:
            error_count += len(batch)
            errors.append(f"Batch {batch_num}: {str(e)}")
            print(f"  Batch {batch_num}/{total_batches}: ❌ Error: {str(e)[:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 LOADING COMPLETE")
    print(f"  Successfully inserted: {success_count} records")
    if error_count > 0:
        print(f"  Failed: {error_count} records")
        print("\n  Errors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"    - {error}")
    
    # Verify data
    print("\n🔍 Verifying staging table...")
    
    # Total count
    total = supabase.table('zooplus_staging').select('count', count='exact').execute()
    print(f"  Total records: {total.count}")
    
    # With ingredients
    with_ingredients = supabase.table('zooplus_staging').select('count', count='exact')\
        .eq('has_ingredients', True).execute()
    print(f"  With ingredients: {with_ingredients.count}")
    
    # Food type breakdown
    print("\n  Food type distribution:")
    for food_type in ['wet', 'dry', 'unknown']:
        count = supabase.table('zooplus_staging').select('count', count='exact')\
            .eq('food_type', food_type).execute()
        print(f"    {food_type}: {count.count}")
    
    # Top brands
    print("\n  Top brands (sample):")
    sample = supabase.table('zooplus_staging').select('brand').limit(100).execute()
    if sample.data:
        brands = {}
        for row in sample.data:
            brand = row['brand']
            brands[brand] = brands.get(brand, 0) + 1
        
        for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {brand}: {count} products (in sample)")
    
    print("\n✅ Data successfully loaded into staging table!")
    print("📝 Next step: Run matching algorithm to identify duplicates")

if __name__ == "__main__":
    main()
