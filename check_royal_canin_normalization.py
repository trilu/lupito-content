#!/usr/bin/env python3
"""
Check if brand normalization was applied to foods_canonical, focusing on Royal Canin
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_royal_canin():
    print("=== ROYAL CANIN BRAND ANALYSIS ===\n")
    
    # Search for all variations of Royal Canin
    print("1. Searching for Royal Canin variations in foods_canonical...")
    
    # Get all products with "Royal" or "Canin" in brand
    response = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').execute()
    all_products = pd.DataFrame(response.data)
    
    # Filter for Royal Canin related
    royal_canin_variations = []
    for _, row in all_products.iterrows():
        if row['brand'] and ('royal' in row['brand'].lower() or 'canin' in row['brand'].lower()):
            royal_canin_variations.append(row)
    
    if royal_canin_variations:
        df_royal = pd.DataFrame(royal_canin_variations)
        
        print(f"\nFound {len(df_royal)} products with 'Royal' or 'Canin' in brand")
        
        # Group by brand to see variations
        brand_counts = df_royal['brand'].value_counts()
        
        print("\n2. Brand variations found:")
        print("-" * 50)
        for brand, count in brand_counts.items():
            print(f"  '{brand}': {count} products")
        
        # Check brand_slug variations
        slug_counts = df_royal['brand_slug'].value_counts()
        
        print("\n3. Brand slug variations:")
        print("-" * 50)
        for slug, count in slug_counts.items():
            print(f"  '{slug}': {count} products")
        
        # Show sample products for each brand variation
        print("\n4. Sample products by brand:")
        print("-" * 50)
        for brand in brand_counts.index[:5]:  # Show first 5 variations
            sample = df_royal[df_royal['brand'] == brand].head(3)
            print(f"\n  Brand: '{brand}'")
            for _, row in sample.iterrows():
                print(f"    - {row['product_name'][:60]}")
                print(f"      Key: {row['product_key'][:50]}...")
    else:
        print("  No Royal Canin products found!")
    
    # Check brand_alias table for Royal Canin
    print("\n5. Checking brand_alias table for Royal Canin mappings...")
    print("-" * 50)
    
    try:
        response = supabase.table('brand_alias').select('*').execute()
        aliases = pd.DataFrame(response.data)
        
        # Filter for Royal Canin related
        royal_aliases = aliases[
            (aliases['canonical_brand'].str.contains('Royal', case=False, na=False)) |
            (aliases['alias'].str.contains('royal', case=False, na=False))
        ]
        
        if not royal_aliases.empty:
            print(f"  Found {len(royal_aliases)} Royal Canin aliases:")
            for _, row in royal_aliases.iterrows():
                print(f"    '{row['alias']}' → '{row['canonical_brand']}'")
        else:
            print("  No Royal Canin aliases found in brand_alias table")
    except Exception as e:
        print(f"  Error checking brand_alias: {e}")
    
    # Check if normalization was supposed to happen
    print("\n6. Expected vs Actual State:")
    print("-" * 50)
    
    expected_brands = ['Royal Canin Breed', 'Royal Canin Veterinary', 'Royal Canin']
    
    for expected in expected_brands:
        count = len(df_royal[df_royal['brand'] == expected]) if 'df_royal' in locals() else 0
        if count > 0:
            print(f"  ✅ '{expected}': {count} products")
        else:
            print(f"  ❌ '{expected}': NOT FOUND")
    
    # Check for non-normalized versions
    print("\n7. Checking for non-normalized brand names:")
    print("-" * 50)
    
    if 'df_royal' in locals():
        non_standard = df_royal[~df_royal['brand'].isin(['Royal Canin', 'Royal Canin Breed'])]
        if not non_standard.empty:
            print(f"  ⚠️ Found {len(non_standard)} products with non-standard brand names:")
            for brand in non_standard['brand'].unique():
                count = len(non_standard[non_standard['brand'] == brand])
                print(f"    '{brand}': {count} products")
        else:
            print("  ✅ All Royal Canin products have standard brand names")

def check_normalization_status():
    """Check if any normalization was applied"""
    print("\n\n=== OVERALL NORMALIZATION CHECK ===\n")
    
    # Get brand distribution
    response = supabase.table('foods_canonical').select('brand').execute()
    df = pd.DataFrame(response.data)
    
    brand_counts = df['brand'].value_counts()
    
    # Check for brands that should have been normalized
    brands_to_check = {
        'Arden Grange': 'Should have products (was Arden)',
        'Barking Heads': 'Should have products (was Barking)',
        'Bosch': 'Should be capitalized (was bosch)',
        'Arden': 'Should be gone (normalized to Arden Grange)',
        'Barking': 'Should be gone (normalized to Barking Heads)',
        'bosch': 'Should be gone (normalized to Bosch)'
    }
    
    print("Checking key normalizations:")
    print("-" * 50)
    
    for brand, expected in brands_to_check.items():
        count = brand_counts.get(brand, 0)
        if 'Should have' in expected and count > 0:
            print(f"  ✅ '{brand}': {count} products - {expected}")
        elif 'Should be gone' in expected and count == 0:
            print(f"  ✅ '{brand}': REMOVED - {expected}")
        elif 'Should be capitalized' in expected and count > 0:
            print(f"  ✅ '{brand}': {count} products - {expected}")
        else:
            print(f"  ❌ '{brand}': {count} products - {expected}")

def main():
    analyze_royal_canin()
    check_normalization_status()
    
    print("\n" + "="*50)
    print("CONCLUSION")
    print("="*50)
    print("""
Based on the analysis above:
- If Royal Canin products still show 'Royal Canin Breed' instead of 'Royal Canin',
  the normalization may not have been applied to those products.
- Check if the brand normalization script ran successfully and committed changes.
- The brand_alias table should contain the mapping but may not have been applied.
""")

if __name__ == "__main__":
    main()