#!/usr/bin/env python3
"""
Fix Royal Canin brand normalization that was missed in the initial run.
The screenshot shows products exist with brands like "Royal Canin Breed" and "Royal Canin Care Nutrition"
that should have been normalized to just "Royal Canin".
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_royal_canin_issue():
    """Deep analysis of why Royal Canin wasn't normalized"""
    print("=" * 70)
    print("ROYAL CANIN NORMALIZATION ISSUE ANALYSIS")
    print("=" * 70)
    
    # Get ALL products with Royal Canin in the brand name
    response = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').execute()
    all_products = pd.DataFrame(response.data)
    
    # Find all Royal Canin variations
    royal_canin_products = all_products[
        all_products['brand'].str.contains('Royal Canin', case=False, na=False)
    ]
    
    print(f"\n1. Found {len(royal_canin_products)} Royal Canin products")
    
    # Group by brand to see all variations
    brand_variations = royal_canin_products['brand'].value_counts()
    
    print("\n2. Current Royal Canin brand variations in database:")
    print("-" * 50)
    for brand, count in brand_variations.items():
        print(f"   '{brand}': {count} products")
    
    # Check what's in brand_alias table
    print("\n3. Checking brand_alias table for Royal Canin mappings...")
    response = supabase.table('brand_alias').select('*').execute()
    aliases = pd.DataFrame(response.data)
    
    royal_aliases = aliases[
        (aliases['canonical_brand'] == 'Royal Canin') |
        (aliases['alias'].str.contains('royal canin', case=False, na=False))
    ]
    
    if not royal_aliases.empty:
        print(f"   Found {len(royal_aliases)} Royal Canin aliases configured:")
        for _, row in royal_aliases.iterrows():
            print(f"     '{row['alias']}' → '{row['canonical_brand']}'")
    else:
        print("   WARNING: No Royal Canin aliases found!")
    
    # Identify the problem
    print("\n4. PROBLEM IDENTIFICATION:")
    print("-" * 50)
    
    # Check if the exact variations are in alias table
    missing_mappings = []
    for brand in brand_variations.index:
        brand_lower = brand.lower().strip()
        if not royal_aliases[royal_aliases['alias'] == brand_lower].empty:
            print(f"   ✅ Mapping exists for '{brand}' but wasn't applied")
        else:
            print(f"   ❌ NO mapping for '{brand}' in brand_alias table")
            missing_mappings.append(brand)
    
    return royal_canin_products, missing_mappings

def fix_royal_canin_normalization():
    """Apply the correct normalization to all Royal Canin products"""
    
    print("\n" + "=" * 70)
    print("FIXING ROYAL CANIN NORMALIZATION")
    print("=" * 70)
    
    # Get all Royal Canin products that need fixing
    response = supabase.table('foods_canonical').select('*').execute()
    all_products = pd.DataFrame(response.data)
    
    # Find products to fix - any with "Royal Canin" but not exactly "Royal Canin"
    products_to_fix = all_products[
        (all_products['brand'].str.contains('Royal Canin', case=False, na=False)) &
        (all_products['brand'] != 'Royal Canin')
    ]
    
    if products_to_fix.empty:
        print("✅ No Royal Canin products need fixing!")
        return
    
    print(f"\nFound {len(products_to_fix)} products to normalize to 'Royal Canin'")
    
    # Group by current brand
    print("\nProducts to fix by brand:")
    for brand, group in products_to_fix.groupby('brand'):
        print(f"  {brand}: {len(group)} products")
    
    # First, ensure we have the alias mappings
    print("\n1. Adding missing alias mappings...")
    new_aliases = []
    
    for brand in products_to_fix['brand'].unique():
        brand_lower = brand.lower().strip()
        
        # Check if alias already exists
        check = supabase.table('brand_alias').select('*').eq('alias', brand_lower).execute()
        
        if not check.data:
            # Add the missing alias
            new_alias = {
                'alias': brand_lower,
                'canonical_brand': 'Royal Canin',
                'created_at': datetime.now().isoformat()
            }
            new_aliases.append(new_alias)
            print(f"  Adding alias: '{brand_lower}' → 'Royal Canin'")
    
    if new_aliases:
        result = supabase.table('brand_alias').insert(new_aliases).execute()
        print(f"  ✅ Added {len(new_aliases)} new alias mappings")
    else:
        print("  ✅ All necessary aliases already exist")
    
    # Now apply the normalization
    print("\n2. Normalizing products...")
    
    # Create rollback data
    rollback_data = []
    updates_made = 0
    
    for _, product in products_to_fix.iterrows():
        old_brand = product['brand']
        old_slug = product['brand_slug']
        old_key = product['product_key']
        
        # New values
        new_brand = 'Royal Canin'
        new_slug = 'royal-canin'
        
        # Reconstruct product key with new brand slug
        key_parts = old_key.split('|')
        if len(key_parts) >= 2:
            key_parts[0] = new_slug
            new_key = '|'.join(key_parts)
        else:
            # Fallback if key format is unexpected
            new_key = old_key.replace(old_slug, new_slug)
        
        # Store rollback info
        rollback_data.append({
            'product_key': old_key,
            'old_brand': old_brand,
            'new_brand': new_brand,
            'old_brand_slug': old_slug,
            'new_brand_slug': new_slug,
            'old_product_key': old_key,
            'new_product_key': new_key
        })
        
        # Update the product
        update_data = {
            'brand': new_brand,
            'brand_slug': new_slug,
            'product_key': new_key
        }
        
        try:
            result = supabase.table('foods_canonical').update(update_data).eq('product_key', old_key).execute()
            updates_made += 1
            
            if updates_made % 10 == 0:
                print(f"  Updated {updates_made}/{len(products_to_fix)} products...")
        except Exception as e:
            print(f"  ⚠️ Error updating {old_key}: {e}")
    
    print(f"\n✅ Successfully normalized {updates_made} Royal Canin products")
    
    # Save rollback data
    rollback_file = f'data/rollback/royal_canin_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    os.makedirs('data/rollback', exist_ok=True)
    
    with open(rollback_file, 'w') as f:
        json.dump(rollback_data, f, indent=2)
    
    print(f"💾 Rollback data saved to: {rollback_file}")
    
    return updates_made

def verify_fix():
    """Verify the fix was successful"""
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    # Check current state
    response = supabase.table('foods_canonical').select('brand').execute()
    df = pd.DataFrame(response.data)
    
    # Count Royal Canin products
    royal_canin_exact = len(df[df['brand'] == 'Royal Canin'])
    royal_canin_variations = df[df['brand'].str.contains('Royal Canin', case=False, na=False)]
    
    print(f"\n✅ 'Royal Canin' (normalized): {royal_canin_exact} products")
    
    # Check for any remaining variations
    other_variations = royal_canin_variations[royal_canin_variations['brand'] != 'Royal Canin']
    
    if not other_variations.empty:
        print("\n⚠️ Remaining non-normalized variations:")
        for brand in other_variations['brand'].unique():
            count = len(other_variations[other_variations['brand'] == brand])
            print(f"   '{brand}': {count} products")
    else:
        print("✅ No other Royal Canin variations found - normalization complete!")
    
    # Show sample products
    if royal_canin_exact > 0:
        print("\n📦 Sample normalized Royal Canin products:")
        response = supabase.table('foods_canonical').select('product_name, brand, brand_slug').eq('brand', 'Royal Canin').limit(5).execute()
        
        for product in response.data:
            print(f"   - {product['product_name'][:60]}")
            print(f"     Brand: {product['brand']} | Slug: {product['brand_slug']}")

def main():
    # Analyze the issue
    royal_products, missing = analyze_royal_canin_issue()
    
    if not royal_products.empty:
        # Fix the normalization
        print("\n" + "=" * 70)
        print("Do you want to proceed with the fix? This will:")
        print("1. Add any missing alias mappings")
        print("2. Normalize all Royal Canin variations to 'Royal Canin'")
        print("3. Update product keys accordingly")
        print("4. Save rollback data")
        print("=" * 70)
        
        # Auto-proceed for this fix
        print("\n🚀 Proceeding with fix...")
        
        updates = fix_royal_canin_normalization()
        
        if updates > 0:
            # Verify the fix
            verify_fix()
        else:
            print("\n✅ No updates needed - Royal Canin is already normalized!")
    else:
        print("\n✅ No Royal Canin products found that need fixing")

if __name__ == "__main__":
    main()