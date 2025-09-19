#!/usr/bin/env python3
"""
Optimized AADF import - check duplicates on-demand
"""

import os
import json
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from supabase import create_client
import argparse

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def check_exists(product_key: str) -> bool:
    """Quick check if product key exists"""
    result = supabase.table('foods_canonical')\
        .select('product_key')\
        .eq('product_key', product_key)\
        .limit(1)\
        .execute()
    return len(result.data) > 0

def main():
    parser = argparse.ArgumentParser(description='Optimized AADF import')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--input', default='data/aadf/aadf_prepared.json', help='Input file')
    
    args = parser.parse_args()
    
    print("⚡ OPTIMIZED AADF IMPORTER")
    print("=" * 80)
    
    # Load prepared data
    with open(args.input, 'r') as f:
        products = json.load(f)
    
    print(f"Loaded {len(products)} prepared products")
    
    stats = {
        'total': 0,
        'new': 0,
        'duplicates': 0,
        'inserted': 0,
        'errors': 0
    }
    
    new_products = []
    
    print("\n🔍 Checking for duplicates...")
    
    for i, product in enumerate(products):
        stats['total'] += 1
        
        # Check if exists
        if check_exists(product['product_key']):
            stats['duplicates'] += 1
        else:
            stats['new'] += 1
            product['created_at'] = datetime.now().isoformat()
            product['updated_at'] = datetime.now().isoformat()
            # Remove fields that don't exist in database
            product.pop('brand_source', None)
            product.pop('original_name', None)
            product.pop('import_timestamp', None)
            new_products.append(product)
        
        if (i + 1) % 100 == 0:
            print(f"  Checked {i + 1}/{len(products)} - New: {stats['new']}, Duplicates: {stats['duplicates']}")
    
    print(f"\n📊 Found {stats['new']} new products to import")
    
    if new_products and not args.dry_run:
        print(f"\n📝 Inserting {len(new_products)} new products...")
        
        # Insert in batches of 50
        for i in range(0, len(new_products), 50):
            batch = new_products[i:i+50]
            try:
                supabase.table('foods_canonical').insert(batch).execute()
                stats['inserted'] += len(batch)
                print(f"  Inserted batch {i//50 + 1}/{(len(new_products)-1)//50 + 1}")
            except Exception as e:
                print(f"  Error: {str(e)[:100]}")
                stats['errors'] += len(batch)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total processed: {stats['total']}")
    print(f"New products found: {stats['new']}")
    print(f"Duplicates found: {stats['duplicates']}")
    
    if not args.dry_run:
        print(f"Successfully inserted: {stats['inserted']}")
        print(f"Errors: {stats['errors']}")
        
        # Check final count
        aadf_result = supabase.table('foods_canonical')\
            .select('count', count='exact')\
            .ilike('product_url', '%allaboutdogfood%')\
            .execute()
        
        print(f"\nTotal AADF products in database: {aadf_result.count}")
    else:
        print("\n⚠️  DRY RUN - No changes made")

if __name__ == "__main__":
    main()