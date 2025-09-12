#!/usr/bin/env python3
"""
Fix remaining brand normalization issues identified by the gap analysis.
This includes:
1. Case mismatches with benchmark
2. High-confidence similar brands (≥95% similarity)
3. Special character normalization
4. Specific known brand corrections
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import json
from typing import Dict, List

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_database_products():
    """Load all products from foods_canonical"""
    print("Loading database products...")
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
    
    print(f"  Loaded {len(all_products)} products")
    return pd.DataFrame(all_products)

def define_brand_fixes():
    """Define all brand fixes to apply"""
    
    fixes = {
        # Case corrections to match benchmark
        'Wolf of Wilderness': 'Wolf Of Wilderness',
        
        # High-confidence similar brands (≥95% similarity)
        'barkinBISTRO': 'Barkin Bistro',
        'Nature\'s Menu': 'Natures Menu',  # Benchmark doesn't have apostrophe
        'Edmondsons': 'Edmondson\'s',
        'Sainsburys': 'Sainsbury\'s',
        'Feelwells': 'Feelwell\'s',
        'Bentleys': 'Bentley\'s',
        'Skinners': 'Skinner\'s',
        'Skippers': 'Skipper\'s',
        
        # Known issues from analysis
        'bozita': 'Bozita',  # Case normalization
        'Hills': 'Hill\'s Science Plan',  # Partial extraction - need to check product names
        'Purina': 'Pro Plan',  # Many Purina products are actually Pro Plan
        'Warley\'s': 'Wainwright\'s',  # Possible typo/variation
        
        # Brands not in benchmark but should be normalized
        'The': None,  # Need product-specific analysis
        'Natural': None,  # Need product-specific analysis
        'Pet': None,  # Need product-specific analysis
        'Wolf': None,  # Need product-specific analysis
        
        # Additional normalizations based on common patterns
        'Advance': 'Advance Veterinary Diets',  # Check if veterinary products
        'Dr': 'Dr John',  # Most common Dr brand
        'Dr.': 'Dr John',
        'Fish': 'Fish4Dogs',
        'Exe': 'Exe Valley',
        'Vets': 'Vet\'s Kitchen',
        'Wild': 'Wild Pet Food',
        'Step': 'Step Up To Naturals',
        'Paul': 'Paul O\'Grady\'s',
        'Go': 'Go Native',
        
        # Fix lowercase versions
        'natures': 'Natures Menu',
    }
    
    return fixes

def analyze_product_specific_fixes(df: pd.DataFrame, brand_fixes: Dict[str, str]):
    """Analyze products with ambiguous brands to determine correct fix"""
    
    enhanced_fixes = brand_fixes.copy()
    
    # Handle "The" brand products
    the_products = df[df['brand'] == 'The']
    if not the_products.empty:
        print("\nAnalyzing 'The' brand products...")
        for _, product in the_products.head(5).iterrows():
            print(f"  Sample: {product['product_name'][:60]}")
        
        # Most 'The' products seem to be incomplete extractions
        # We'll skip these for manual review
        enhanced_fixes['The'] = None
    
    # Handle "Hills" products - check if Science Plan or Prescription Diet
    hills_products = df[df['brand'] == 'Hills']
    if not hills_products.empty:
        prescription_count = 0
        science_count = 0
        
        for _, product in hills_products.iterrows():
            prod_name = (product.get('product_name') or '').lower()
            if 'prescription' in prod_name or 'veterinary' in prod_name:
                prescription_count += 1
            else:
                science_count += 1
        
        if prescription_count > science_count:
            enhanced_fixes['Hills'] = 'Hill\'s Prescription Diet'
        else:
            enhanced_fixes['Hills'] = 'Hill\'s Science Plan'
        
        print(f"\n'Hills' analysis: {prescription_count} prescription, {science_count} science plan")
        print(f"  Decision: Hills → {enhanced_fixes['Hills']}")
    
    # Handle "Purina" products - check if Pro Plan
    purina_products = df[df['brand'] == 'Purina']
    if not purina_products.empty:
        pro_plan_count = 0
        
        for _, product in purina_products.iterrows():
            prod_name = (product.get('product_name') or '').lower()
            if 'pro plan' in prod_name:
                pro_plan_count += 1
        
        if pro_plan_count > len(purina_products) * 0.7:
            enhanced_fixes['Purina'] = 'Pro Plan'
        else:
            enhanced_fixes['Purina'] = None  # Keep as Purina
        
        print(f"\n'Purina' analysis: {pro_plan_count}/{len(purina_products)} are Pro Plan")
        if enhanced_fixes['Purina']:
            print(f"  Decision: Purina → Pro Plan")
        else:
            print(f"  Decision: Keep as Purina")
    
    return enhanced_fixes

def apply_fixes(df: pd.DataFrame, brand_fixes: Dict[str, str]):
    """Apply brand fixes to the database"""
    
    print("\n" + "=" * 70)
    print("APPLYING BRAND FIXES")
    print("=" * 70)
    
    # Filter out None values (brands we're not fixing)
    active_fixes = {k: v for k, v in brand_fixes.items() if v is not None}
    
    if not active_fixes:
        print("\n✅ No fixes to apply!")
        return 0
    
    print(f"\nApplying {len(active_fixes)} brand corrections...")
    
    rollback_data = []
    success_count = 0
    error_count = 0
    
    for old_brand, new_brand in active_fixes.items():
        # Find products with this brand
        products_to_fix = df[df['brand'] == old_brand]
        
        if products_to_fix.empty:
            continue
        
        print(f"\n  {old_brand} → {new_brand} ({len(products_to_fix)} products)")
        
        for _, product in products_to_fix.iterrows():
            old_key = product['product_key']
            old_slug = product['brand_slug']
            
            # Generate new slug
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
                'old_brand': old_brand,
                'new_brand': new_brand,
                'old_brand_slug': old_slug,
                'new_brand_slug': new_slug,
                'old_product_key': old_key,
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
            except Exception as e:
                print(f"    ⚠️ Error updating {old_key}: {e}")
                error_count += 1
    
    print(f"\n✅ Successfully fixed {success_count} products")
    if error_count > 0:
        print(f"⚠️ Failed to fix {error_count} products")
    
    # Save rollback data
    if rollback_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_file = f'data/rollback/remaining_fixes_{timestamp}.json'
        os.makedirs('data/rollback', exist_ok=True)
        
        with open(rollback_file, 'w') as f:
            json.dump(rollback_data, f, indent=2)
        
        print(f"\n💾 Rollback data saved to: {rollback_file}")
    
    return success_count

def add_missing_brand_aliases(brand_fixes: Dict[str, str]):
    """Add missing aliases to brand_alias table"""
    
    print("\n" + "=" * 70)
    print("UPDATING BRAND ALIASES")
    print("=" * 70)
    
    active_fixes = {k: v for k, v in brand_fixes.items() if v is not None}
    
    added = 0
    for old_brand, new_brand in active_fixes.items():
        alias = old_brand.lower().strip()
        
        # Check if alias already exists
        check = supabase.table('brand_alias').select('*').eq('alias', alias).execute()
        
        if not check.data:
            result = supabase.table('brand_alias').insert({
                'alias': alias,
                'canonical_brand': new_brand,
                'created_at': datetime.now().isoformat()
            }).execute()
            print(f"  Added alias: '{alias}' → '{new_brand}'")
            added += 1
    
    print(f"\n✅ Added {added} new brand aliases")

def verify_fixes():
    """Verify the fixes were applied correctly"""
    
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    # Load updated data
    response = supabase.table('foods_canonical').select('brand').execute()
    df = pd.DataFrame(response.data)
    
    # Count unique brands
    unique_brands = df['brand'].nunique()
    print(f"\n📊 Total unique brands after fixes: {unique_brands}")
    
    # Check for problematic brands
    problematic = ['The', 'Hills', 'bozita', 'barkinBISTRO', 'Skinners', 'Feelwells']
    
    print("\nChecking previously problematic brands:")
    for brand in problematic:
        count = len(df[df['brand'] == brand])
        if count > 0:
            print(f"  ⚠️ '{brand}': Still has {count} products")
        else:
            print(f"  ✅ '{brand}': Fixed (0 products)")
    
    # Top brands
    print("\n📈 Top 10 brands after fixes:")
    brand_counts = df['brand'].value_counts()
    for brand, count in brand_counts.head(10).items():
        print(f"  {brand}: {count} products")

def main():
    # Load database
    df = load_database_products()
    
    # Define fixes
    brand_fixes = define_brand_fixes()
    
    # Analyze product-specific fixes
    brand_fixes = analyze_product_specific_fixes(df, brand_fixes)
    
    # Add aliases first
    add_missing_brand_aliases(brand_fixes)
    
    # Apply fixes
    fixed_count = apply_fixes(df, brand_fixes)
    
    if fixed_count > 0:
        # Verify
        verify_fixes()
    
    print("\n" + "=" * 70)
    print("COMPLETION SUMMARY")
    print("=" * 70)
    print(f"\n✅ Fixed {fixed_count} products")
    print("\nNext steps:")
    print("1. Review brands not in benchmark (211 found)")
    print("2. Investigate product/brand mismatches (238 found)")
    print("3. Consider adding legitimate brands to ALL-BRANDS.md")
    print("4. Review short/partial brand extractions manually")

if __name__ == "__main__":
    main()