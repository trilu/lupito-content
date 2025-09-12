#!/usr/bin/env python3
"""
Apply FULL brand normalization to foods_canonical table.
The previous normalization script didn't actually update the database.
This script will properly apply ALL brand normalizations from brand_alias table.
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
from typing import Dict, List, Tuple

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_current_state() -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Analyze current state of brands in foods_canonical"""
    print("=" * 70)
    print("ANALYZING CURRENT BRAND STATE")
    print("=" * 70)
    
    # Get all products - need to handle pagination
    print("\n1. Loading foods_canonical table...")
    all_products = []
    limit = 1000
    offset = 0
    
    while True:
        response = supabase.table('foods_canonical').select('*').range(offset, offset + limit - 1).execute()
        batch = response.data
        if not batch:
            break
        all_products.extend(batch)
        offset += limit
        print(f"   Loaded {len(all_products)} products...", end='\r')
    
    products_df = pd.DataFrame(all_products)
    print(f"   Loaded {len(products_df)} products total")
    
    # Get brand alias mappings
    print("\n2. Loading brand_alias mappings...")
    response = supabase.table('brand_alias').select('*').execute()
    aliases_df = pd.DataFrame(response.data)
    
    # Create mapping dictionary
    alias_map = {}
    for _, row in aliases_df.iterrows():
        alias_map[row['alias'].lower().strip()] = row['canonical_brand']
    
    print(f"   Loaded {len(alias_map)} brand alias mappings")
    
    # Analyze which brands need normalization
    print("\n3. Analyzing brands that need normalization...")
    brands_to_normalize = []
    
    for brand in products_df['brand'].dropna().unique():
        brand_lower = brand.lower().strip()
        if brand_lower in alias_map and alias_map[brand_lower] != brand:
            canonical = alias_map[brand_lower]
            count = len(products_df[products_df['brand'] == brand])
            brands_to_normalize.append({
                'current_brand': brand,
                'canonical_brand': canonical,
                'product_count': count
            })
    
    if brands_to_normalize:
        print(f"\n   Found {len(brands_to_normalize)} brands that need normalization:")
        print("-" * 50)
        
        # Sort by product count
        brands_to_normalize.sort(key=lambda x: x['product_count'], reverse=True)
        
        total_products = 0
        for item in brands_to_normalize[:20]:  # Show top 20
            print(f"   '{item['current_brand']}' → '{item['canonical_brand']}' ({item['product_count']} products)")
            total_products += item['product_count']
        
        if len(brands_to_normalize) > 20:
            remaining = sum(item['product_count'] for item in brands_to_normalize[20:])
            print(f"   ... and {len(brands_to_normalize) - 20} more brands ({remaining} products)")
            total_products += remaining
        
        print(f"\n   TOTAL: {total_products} products need brand normalization")
    else:
        print("   ✅ No brands need normalization!")
    
    return products_df, alias_map

def apply_normalization(products_df: pd.DataFrame, alias_map: Dict[str, str], dry_run: bool = False):
    """Apply brand normalization to all products"""
    
    print("\n" + "=" * 70)
    print("APPLYING BRAND NORMALIZATION" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 70)
    
    # Track changes
    updates = []
    rollback_data = []
    
    # Process each product
    for idx, product in products_df.iterrows():
        if pd.isna(product['brand']):
            continue
            
        brand_lower = product['brand'].lower().strip()
        
        # Check if brand needs normalization
        if brand_lower in alias_map and alias_map[brand_lower] != product['brand']:
            old_brand = product['brand']
            new_brand = alias_map[brand_lower]
            old_slug = product['brand_slug']
            new_slug = new_brand.lower().replace(' ', '-').replace("'", '').replace('&', 'and')
            old_key = product['product_key']
            
            # Reconstruct product key
            key_parts = old_key.split('|')
            if len(key_parts) >= 2:
                key_parts[0] = new_slug
                new_key = '|'.join(key_parts)
            else:
                new_key = old_key
            
            updates.append({
                'product_key': old_key,
                'brand': new_brand,
                'brand_slug': new_slug,
                'new_product_key': new_key
            })
            
            rollback_data.append({
                'product_key': old_key,
                'old_brand': old_brand,
                'new_brand': new_brand,
                'old_brand_slug': old_slug,
                'new_brand_slug': new_slug,
                'old_product_key': old_key,
                'new_product_key': new_key
            })
    
    if not updates:
        print("\n✅ No products need normalization!")
        return 0
    
    print(f"\nFound {len(updates)} products to normalize")
    
    # Group by brand change for summary
    brand_changes = {}
    for item in rollback_data:
        key = f"{item['old_brand']} → {item['new_brand']}"
        brand_changes[key] = brand_changes.get(key, 0) + 1
    
    print("\nBrand normalization summary:")
    print("-" * 50)
    for change, count in sorted(brand_changes.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {change}: {count} products")
    
    if len(brand_changes) > 20:
        print(f"  ... and {len(brand_changes) - 20} more brand changes")
    
    if dry_run:
        print("\n⚠️ DRY RUN - No changes made to database")
        return len(updates)
    
    # Apply updates
    print(f"\nApplying {len(updates)} updates...")
    
    success_count = 0
    error_count = 0
    batch_size = 50
    
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        
        for update in batch:
            old_key = update['product_key']
            new_data = {
                'brand': update['brand'],
                'brand_slug': update['brand_slug'],
                'product_key': update['new_product_key']
            }
            
            try:
                result = supabase.table('foods_canonical').update(new_data).eq('product_key', old_key).execute()
                success_count += 1
            except Exception as e:
                print(f"  ⚠️ Error updating {old_key}: {e}")
                error_count += 1
        
        print(f"  Progress: {min(i+batch_size, len(updates))}/{len(updates)} processed...")
    
    print(f"\n✅ Successfully normalized {success_count} products")
    if error_count > 0:
        print(f"⚠️ Failed to update {error_count} products")
    
    # Save rollback data
    if rollback_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_file = f'data/rollback/full_normalization_{timestamp}.json'
        os.makedirs('data/rollback', exist_ok=True)
        
        with open(rollback_file, 'w') as f:
            json.dump(rollback_data, f, indent=2)
        
        print(f"\n💾 Rollback data saved to: {rollback_file}")
    
    return success_count

def verify_normalization():
    """Verify normalization was successful"""
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    # Get current state
    response = supabase.table('foods_canonical').select('brand').execute()
    df = pd.DataFrame(response.data)
    
    # Get brand alias mappings
    response = supabase.table('brand_alias').select('*').execute()
    aliases_df = pd.DataFrame(response.data)
    alias_map = {row['alias'].lower().strip(): row['canonical_brand'] 
                 for _, row in aliases_df.iterrows()}
    
    # Check for non-normalized brands
    non_normalized = []
    for brand in df['brand'].dropna().unique():
        brand_lower = brand.lower().strip()
        if brand_lower in alias_map and alias_map[brand_lower] != brand:
            count = len(df[df['brand'] == brand])
            non_normalized.append((brand, alias_map[brand_lower], count))
    
    if non_normalized:
        print("\n⚠️ Still found non-normalized brands:")
        for current, canonical, count in non_normalized[:10]:
            print(f"   '{current}' should be '{canonical}' ({count} products)")
    else:
        print("\n✅ All brands are properly normalized!")
    
    # Show top brands
    print("\n📊 Top 20 brands after normalization:")
    brand_counts = df['brand'].value_counts()
    for brand, count in brand_counts.head(20).items():
        print(f"   {brand}: {count} products")
    
    print(f"\n📈 Total unique brands: {df['brand'].nunique()}")

def main():
    # Analyze current state
    products_df, alias_map = analyze_current_state()
    
    if not alias_map:
        print("\n⚠️ No brand aliases found in brand_alias table!")
        return
    
    # Check if we need to apply normalization
    print("\n" + "=" * 70)
    print("Ready to apply normalization")
    print("=" * 70)
    
    # First do a dry run
    print("\nPerforming dry run first...")
    updates_needed = apply_normalization(products_df, alias_map, dry_run=True)
    
    if updates_needed > 0:
        print("\n" + "=" * 70)
        print(f"APPLYING NORMALIZATION TO {updates_needed} PRODUCTS")
        print("=" * 70)
        
        # Apply the actual normalization
        success_count = apply_normalization(products_df, alias_map, dry_run=False)
        
        if success_count > 0:
            # Verify the results
            verify_normalization()
    else:
        print("\n✅ Database is already fully normalized!")

if __name__ == "__main__":
    main()