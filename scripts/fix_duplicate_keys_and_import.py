#!/usr/bin/env python3
"""
Fix duplicate product keys and import remaining products
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime
from collections import defaultdict

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def main():
    print("🔧 FIXING DUPLICATE KEYS AND IMPORTING REMAINING PRODUCTS")
    print("=" * 60)
    
    # Connect to Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get unprocessed new products from staging
    print("Loading unprocessed new products from staging...")
    new_products = supabase.table('zooplus_staging').select('*')\
        .eq('match_type', 'new')\
        .eq('processed', False)\
        .execute()
    
    print(f"  Found {len(new_products.data)} unprocessed products")
    
    # Group by product key to find duplicates
    products_by_key = defaultdict(list)
    for product in new_products.data:
        products_by_key[product['product_key']].append(product)
    
    # Fix duplicate keys
    print("\nPreparing products with unique keys...")
    products_to_import = []
    fixed_duplicates = 0
    
    for product_key, products in products_by_key.items():
        if len(products) == 1:
            # No duplicate, use as is
            product = products[0]
        else:
            # Multiple products with same key - pick the one with ingredients if available
            products_with_ingredients = [p for p in products if p.get('has_ingredients')]
            if products_with_ingredients:
                product = products_with_ingredients[0]
            else:
                product = products[0]  # Just take the first one
            fixed_duplicates += len(products) - 1
        
        # Skip if no product name
        if not product.get('product_name'):
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
        
        products_to_import.append((product['id'], canonical_product))
    
    print(f"  Ready to import: {len(products_to_import)} unique products")
    print(f"  Skipped duplicates: {fixed_duplicates}")
    
    # Check which keys already exist in database
    print("\nChecking for existing products in database...")
    product_keys = [p[1]['product_key'] for p in products_to_import]
    
    # Check in batches
    existing_keys = set()
    batch_size = 100
    for i in range(0, len(product_keys), batch_size):
        batch_keys = product_keys[i:i+batch_size]
        existing = supabase.table('foods_canonical').select('product_key')\
            .in_('product_key', batch_keys).execute()
        existing_keys.update(p['product_key'] for p in existing.data)
    
    # Filter out existing products
    final_products = []
    skipped_existing = 0
    for staging_id, product in products_to_import:
        if product['product_key'] not in existing_keys:
            final_products.append((staging_id, product))
        else:
            skipped_existing += 1
            # Mark as processed anyway since it's already in the database
            supabase.table('zooplus_staging').update({
                'processed': True,
                'match_type': 'existing_after_import'
            }).eq('id', staging_id).execute()
    
    print(f"  Products to import: {len(final_products)}")
    print(f"  Already exist in database: {skipped_existing}")
    
    if not final_products:
        print("\n✅ All products already in database!")
        return
    
    # Import in batches
    print("\nImporting products...")
    batch_size = 50
    total_batches = (len(final_products) + batch_size - 1) // batch_size
    
    success_count = 0
    error_count = 0
    
    for i in range(0, len(final_products), batch_size):
        batch = final_products[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        # Extract just the product data for insertion
        products_batch = [p[1] for p in batch]
        staging_ids = [p[0] for p in batch]
        
        try:
            result = supabase.table('foods_canonical').insert(products_batch).execute()
            success_count += len(batch)
            print(f"  Batch {batch_num}/{total_batches}: ✅ {len(batch)} products imported")
            
            # Update staging to mark as processed
            for sid in staging_ids:
                supabase.table('zooplus_staging').update({
                    'processed': True
                }).eq('id', sid).execute()
                
        except Exception as e:
            error_count += len(batch)
            print(f"  Batch {batch_num}/{total_batches}: ❌ Error: {str(e)[:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 IMPORT COMPLETE")
    print(f"  Successfully imported: {success_count} products")
    print(f"  Failed: {error_count} products")
    print(f"  Skipped (duplicates): {fixed_duplicates}")
    print(f"  Skipped (already in DB): {skipped_existing}")
    
    # Verify new database size
    new_count = supabase.table('foods_canonical').select('count', count='exact').execute()
    print(f"\n  Current database size: {new_count.count} products")
    
    # Check coverage
    with_ingredients = supabase.table('foods_canonical').select('count', count='exact')\
        .not_.is_('ingredients_raw', 'null').execute()
    
    coverage = (with_ingredients.count / new_count.count) * 100
    print(f"  Ingredient coverage: {with_ingredients.count}/{new_count.count} ({coverage:.1f}%)")
    
    print("\n✅ Import complete!")

if __name__ == "__main__":
    main()