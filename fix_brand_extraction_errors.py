#!/usr/bin/env python3
"""
Fix incorrect brand extractions and normalize all Royal Canin variations.
Many products have partial brand names like "Royal", "The", "Natures" etc.
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
import re

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def identify_brand_issues():
    """Identify and fix incorrect brand extractions"""
    print("=" * 70)
    print("IDENTIFYING BRAND EXTRACTION ISSUES")
    print("=" * 70)
    
    # Load all products with pagination
    print("\n1. Loading all products...")
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
    
    df = pd.DataFrame(all_products)
    print(f"   Loaded {len(df)} products")
    
    # Define brand corrections based on product names
    brand_corrections = {
        # Royal Canin variations
        'Royal': 'Royal Canin',
        'Royal Canin Veterinary & Expert': 'Royal Canin',
        'Royal Canin Size': 'Royal Canin',
        'Royal Canin Care Nutrition': 'Royal Canin',
        'Royal Canin Club': 'Royal Canin',
        
        # Other incomplete extractions
        'The': None,  # Need to check product names
        'Natures': "Nature's Menu",
        'Happy': 'Happy Dog',
        'Pets': 'Pets at Home',
        'James': 'James Wellbeloved',
        'Lilys': "Lily's Kitchen",
        'Natural': None,  # Need to check
        'Yorkshires': 'Yorkshire Valley Farms',
        'Lakes': 'Lakes Heritage',
        'Warleys': "Warley's",
        'Wainwrights': "Wainwright's",
    }
    
    # Analyze products needing correction
    products_to_fix = []
    
    for _, product in df.iterrows():
        current_brand = product['brand']
        product_name = product['product_name'] or ''
        
        # Check if brand needs correction
        if current_brand in brand_corrections:
            new_brand = brand_corrections[current_brand]
            
            # For ambiguous brands, try to determine from product name
            if new_brand is None:
                if current_brand == 'The':
                    if 'The Hunger of the Wolf' in product_name:
                        new_brand = 'The Hunger of the Wolf'
                    elif 'The Natural Pet' in product_name:
                        new_brand = 'The Natural Pet Company'
                    else:
                        # Try to extract full brand from product name
                        match = re.match(r'^(The [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', product_name)
                        if match:
                            new_brand = match.group(1)
                
                elif current_brand == 'Natural':
                    if 'Natural Dog Food Company' in product_name:
                        new_brand = 'Natural Dog Food Company'
                    elif 'Natural Balance' in product_name:
                        new_brand = 'Natural Balance'
                    else:
                        continue  # Skip if can't determine
            
            if new_brand:
                products_to_fix.append({
                    'product_key': product['product_key'],
                    'current_brand': current_brand,
                    'new_brand': new_brand,
                    'product_name': product_name[:60]
                })
    
    # Also find products where brand doesn't match product name
    print("\n2. Finding brand/product name mismatches...")
    
    for _, product in df.iterrows():
        product_name = (product['product_name'] or '').lower()
        current_brand = product['brand'] or ''
        
        # Check for Royal Canin in name but different brand
        if 'royal canin' in product_name and 'Royal Canin' not in current_brand:
            products_to_fix.append({
                'product_key': product['product_key'],
                'current_brand': current_brand,
                'new_brand': 'Royal Canin',
                'product_name': product['product_name'][:60]
            })
        
        # Check for other major brands in name
        brand_patterns = [
            ("hill's", "Hill's"),
            ('purina', 'Purina'),
            ('iams', 'Iams'),
            ('eukanuba', 'Eukanuba'),
            ('advance', 'Advance'),
            ('brit', 'Brit'),
            ('acana', 'Acana'),
            ('orijen', 'Orijen')
        ]
        
        for pattern, correct_brand in brand_patterns:
            if pattern in product_name and pattern not in current_brand.lower():
                # Only fix if it's a clear mismatch
                if len(current_brand) <= 10 or current_brand in ['The', 'Natural', 'Happy']:
                    products_to_fix.append({
                        'product_key': product['product_key'],
                        'current_brand': current_brand,
                        'new_brand': correct_brand,
                        'product_name': product['product_name'][:60]
                    })
                    break
    
    return df, products_to_fix

def apply_brand_fixes(products_to_fix):
    """Apply the brand fixes to the database"""
    
    if not products_to_fix:
        print("\n✅ No products need brand correction!")
        return 0
    
    print("\n" + "=" * 70)
    print(f"APPLYING BRAND FIXES TO {len(products_to_fix)} PRODUCTS")
    print("=" * 70)
    
    # Group by brand change
    brand_changes = {}
    for fix in products_to_fix:
        key = f"{fix['current_brand']} → {fix['new_brand']}"
        if key not in brand_changes:
            brand_changes[key] = []
        brand_changes[key].append(fix)
    
    # Show summary
    print("\nBrand corrections to apply:")
    print("-" * 50)
    for change, items in sorted(brand_changes.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        print(f"  {change}: {len(items)} products")
        # Show sample products
        for item in items[:2]:
            print(f"    • {item['product_name']}")
    
    if len(brand_changes) > 20:
        print(f"  ... and {len(brand_changes) - 20} more brand corrections")
    
    # Apply fixes
    print("\nApplying fixes...")
    rollback_data = []
    success_count = 0
    error_count = 0
    
    for fix in products_to_fix:
        old_key = fix['product_key']
        new_brand = fix['new_brand']
        new_slug = new_brand.lower().replace(' ', '-').replace("'", '').replace('&', 'and')
        
        # Reconstruct product key
        key_parts = old_key.split('|')
        if len(key_parts) >= 2:
            key_parts[0] = new_slug
            new_key = '|'.join(key_parts)
        else:
            new_key = old_key
        
        # Store rollback info
        rollback_data.append({
            'product_key': old_key,
            'old_brand': fix['current_brand'],
            'new_brand': new_brand,
            'new_product_key': new_key
        })
        
        # Update product
        update_data = {
            'brand': new_brand,
            'brand_slug': new_slug,
            'product_key': new_key
        }
        
        try:
            result = supabase.table('foods_canonical').update(update_data).eq('product_key', old_key).execute()
            success_count += 1
            
            if success_count % 50 == 0:
                print(f"  Progress: {success_count}/{len(products_to_fix)} fixed...")
        except Exception as e:
            print(f"  ⚠️ Error updating {old_key}: {e}")
            error_count += 1
    
    print(f"\n✅ Successfully fixed {success_count} products")
    if error_count > 0:
        print(f"⚠️ Failed to fix {error_count} products")
    
    # Save rollback data
    if rollback_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_file = f'data/rollback/brand_extraction_fixes_{timestamp}.json'
        os.makedirs('data/rollback', exist_ok=True)
        
        with open(rollback_file, 'w') as f:
            json.dump(rollback_data, f, indent=2)
        
        print(f"\n💾 Rollback data saved to: {rollback_file}")
    
    return success_count

def add_missing_aliases():
    """Add any missing brand aliases to brand_alias table"""
    print("\n" + "=" * 70)
    print("ADDING MISSING BRAND ALIASES")
    print("=" * 70)
    
    new_aliases = [
        ('royal', 'Royal Canin'),
        ('royal canin veterinary & expert', 'Royal Canin'),
        ('royal canin size', 'Royal Canin'),
        ('royal canin care nutrition', 'Royal Canin'),
        ('royal canin club', 'Royal Canin'),
        ('natures', "Nature's Menu"),
        ('happy', 'Happy Dog'),
        ('pets', 'Pets at Home'),
        ('james', 'James Wellbeloved'),
        ('lilys', "Lily's Kitchen"),
        ('yorkshires', 'Yorkshire Valley Farms'),
        ('lakes', 'Lakes Heritage'),
        ('warleys', "Warley's"),
        ('wainwrights', "Wainwright's"),
    ]
    
    added = 0
    for alias, canonical in new_aliases:
        # Check if exists
        check = supabase.table('brand_alias').select('*').eq('alias', alias).execute()
        
        if not check.data:
            result = supabase.table('brand_alias').insert({
                'alias': alias,
                'canonical_brand': canonical,
                'created_at': datetime.now().isoformat()
            }).execute()
            print(f"  Added: '{alias}' → '{canonical}'")
            added += 1
    
    print(f"\n✅ Added {added} new brand aliases")

def main():
    # Add missing aliases first
    add_missing_aliases()
    
    # Identify issues
    df, products_to_fix = identify_brand_issues()
    
    print(f"\n3. Found {len(products_to_fix)} products needing brand correction")
    
    if products_to_fix:
        # Remove duplicates
        seen = set()
        unique_fixes = []
        for fix in products_to_fix:
            key = fix['product_key']
            if key not in seen:
                seen.add(key)
                unique_fixes.append(fix)
        
        print(f"   After deduplication: {len(unique_fixes)} unique products to fix")
        
        # Apply fixes
        apply_brand_fixes(unique_fixes)
        
        # Verify
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)
        
        # Check Royal Canin specifically
        response = supabase.table('foods_canonical').select('brand').execute()
        verify_df = pd.DataFrame(response.data)
        
        royal_count = len(verify_df[verify_df['brand'] == 'Royal Canin'])
        print(f"\n✅ Royal Canin products after fix: {royal_count}")
        
        # Check for problematic brands
        problematic = ['Royal', 'The', 'Natures', 'Happy', 'Pets', 'James']
        print("\nChecking problematic brands:")
        for brand in problematic:
            count = len(verify_df[verify_df['brand'] == brand])
            if count > 0:
                print(f"  ⚠️ '{brand}': Still has {count} products")
            else:
                print(f"  ✅ '{brand}': Fixed (0 products)")

if __name__ == "__main__":
    main()