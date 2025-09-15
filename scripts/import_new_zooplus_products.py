#!/usr/bin/env python3
"""
Import new Zooplus products from staging to main database
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    print("📥 IMPORTING NEW ZOOPLUS PRODUCTS")
    print("=" * 60)
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get new products from staging
    print("Loading new products from staging...")
    new_products = supabase.table('zooplus_staging').select('*')\
        .eq('match_type', 'new')\
        .eq('is_variant', False)\
        .execute()
    
    print(f"  Found {len(new_products.data)} new products to import")
    
    # Check current database size
    current_count = supabase.table('foods_canonical').select('count', count='exact').execute()
    print(f"  Current database size: {current_count.count} products")
    
    # Prepare products for import
    print("\nPreparing products for import...")
    
    products_to_import = []
    skipped = 0
    
    for product in new_products.data:
        # Skip if no product name
        if not product.get('product_name'):
            skipped += 1
            continue
        
        # Prepare record for foods_canonical
        canonical_product = {
            'product_key': product['product_key'],
            'brand': product.get('brand'),
            'product_name': product['product_name'],
            'product_url': product.get('product_url'),
            'ingredients_raw': product.get('ingredients_preview') if product.get('has_ingredients') else None,
            'source': 'zooplus_csv_import',
            'updated_at': datetime.now().isoformat()
        }
        
        # Add food type if available
        if product.get('food_type') and product['food_type'] != 'unknown':
            canonical_product['form'] = product['food_type']
        
        products_to_import.append(canonical_product)
    
    print(f"  Ready to import: {len(products_to_import)} products")
    if skipped > 0:
        print(f"  Skipped: {skipped} products (missing required data)")
    
    # Auto-confirm for programmatic execution
    print("\n✅ Proceeding with import...")
    
    # Import in batches
    print("\nImporting products...")
    batch_size = 50
    total_batches = (len(products_to_import) + batch_size - 1) // batch_size
    
    success_count = 0
    error_count = 0
    errors = []
    
    for i in range(0, len(products_to_import), batch_size):
        batch = products_to_import[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        try:
            result = supabase.table('foods_canonical').insert(batch).execute()
            success_count += len(batch)
            print(f"  Batch {batch_num}/{total_batches}: ✅ {len(batch)} products imported")
            
            # Update staging to mark as processed
            staging_ids = [p['id'] for p in new_products.data[i:i+batch_size]]
            for sid in staging_ids:
                supabase.table('zooplus_staging').update({
                    'processed': True
                }).eq('id', sid).execute()
                
        except Exception as e:
            error_count += len(batch)
            error_msg = str(e)
            errors.append(f"Batch {batch_num}: {error_msg[:100]}")
            print(f"  Batch {batch_num}/{total_batches}: ❌ Error: {error_msg[:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 IMPORT COMPLETE")
    print(f"  Successfully imported: {success_count} products")
    
    if error_count > 0:
        print(f"  Failed: {error_count} products")
        print("\n  Errors:")
        for error in errors[:5]:
            print(f"    - {error}")
    
    # Verify new database size
    new_count = supabase.table('foods_canonical').select('count', count='exact').execute()
    print(f"\n  Database size: {current_count.count} → {new_count.count} (+{new_count.count - current_count.count})")
    
    # Check coverage
    with_ingredients = supabase.table('foods_canonical').select('count', count='exact')\
        .not_.is_('ingredients_raw', 'null').execute()
    
    coverage = (with_ingredients.count / new_count.count) * 100
    print(f"  Ingredient coverage: {with_ingredients.count}/{new_count.count} ({coverage:.1f}%)")
    
    # Products needing scraping
    print("\n🎯 Next steps:")
    
    # Count staging products that need scraping
    need_scraping = supabase.table('zooplus_staging').select('count', count='exact')\
        .eq('match_type', 'new')\
        .eq('has_ingredients', False)\
        .execute()
    
    print(f"  - {need_scraping.count} new products need ingredient scraping")
    
    # Count existing products needing scraping
    existing_need_scraping = supabase.table('foods_canonical').select('count', count='exact')\
        .ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null')\
        .execute()
    
    print(f"  - {existing_need_scraping.count} existing products need ingredient scraping")
    print(f"  - Total to scrape: {need_scraping.count + existing_need_scraping.count} products")
    
    print("\n✅ Import successful! Run scraping next to enrich products.")

if __name__ == "__main__":
    main()
