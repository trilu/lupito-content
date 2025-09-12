#!/usr/bin/env python3
"""
Comprehensive verification of brand normalization
"""

import os
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    print("=" * 70)
    print("COMPREHENSIVE BRAND NORMALIZATION VERIFICATION")
    print("=" * 70)
    
    # Load all products with pagination
    print("\n1. Loading all products from foods_canonical...")
    all_products = []
    limit = 1000
    offset = 0
    
    while True:
        response = supabase.table('foods_canonical').select('product_key, brand, brand_slug, product_name').range(offset, offset + limit - 1).execute()
        batch = response.data
        if not batch:
            break
        all_products.extend(batch)
        offset += limit
    
    df = pd.DataFrame(all_products)
    print(f"   Total products: {len(df)}")
    
    # Analyze Royal Canin specifically
    print("\n2. Royal Canin Analysis:")
    print("-" * 50)
    
    # Search for ANY Royal Canin related products
    royal_products = df[
        df['brand'].str.contains('Royal', case=False, na=False) |
        df['product_name'].str.contains('Royal Canin', case=False, na=False)
    ]
    
    print(f"   Products with 'Royal' in brand: {len(df[df['brand'].str.contains('Royal', case=False, na=False)])}")
    print(f"   Products with 'Royal Canin' in name: {len(df[df['product_name'].str.contains('Royal Canin', case=False, na=False)])}")
    print(f"   Total Royal Canin related products: {len(royal_products)}")
    
    if not royal_products.empty:
        # Group by brand
        royal_brands = royal_products['brand'].value_counts()
        print("\n   Royal Canin brand variations:")
        for brand, count in royal_brands.items():
            print(f"     '{brand}': {count} products")
        
        # Show sample products
        print("\n   Sample Royal Canin products:")
        for _, product in royal_products.head(10).iterrows():
            print(f"     - {product['product_name'][:50]}")
            print(f"       Brand: {product['brand']} | Key: {product['product_key'][:40]}...")
    
    # Check brand distribution
    print("\n3. Top 30 Brands After Normalization:")
    print("-" * 50)
    brand_counts = df['brand'].value_counts()
    
    for brand, count in brand_counts.head(30).items():
        marker = "⭐" if "Royal" in brand else "  "
        print(f"{marker} {brand}: {count} products")
    
    # Check for any remaining non-normalized brands
    print("\n4. Checking for Non-Normalized Brands:")
    print("-" * 50)
    
    # Load alias mappings
    response = supabase.table('brand_alias').select('*').execute()
    aliases_df = pd.DataFrame(response.data)
    alias_map = {row['alias'].lower().strip(): row['canonical_brand'] 
                 for _, row in aliases_df.iterrows()}
    
    non_normalized = []
    for brand in df['brand'].dropna().unique():
        brand_lower = brand.lower().strip()
        if brand_lower in alias_map and alias_map[brand_lower] != brand:
            count = len(df[df['brand'] == brand])
            non_normalized.append((brand, alias_map[brand_lower], count))
    
    if non_normalized:
        print("   ⚠️ Found non-normalized brands:")
        for current, canonical, count in non_normalized:
            print(f"     '{current}' should be '{canonical}' ({count} products)")
    else:
        print("   ✅ All brands are properly normalized!")
    
    # Summary statistics
    print("\n5. Summary Statistics:")
    print("-" * 50)
    print(f"   Total products: {len(df)}")
    print(f"   Total unique brands: {df['brand'].nunique()}")
    print(f"   Products with null brand: {df['brand'].isna().sum()}")
    
    # Check specific brands that were normalized
    print("\n6. Verification of Key Normalizations:")
    print("-" * 50)
    
    key_brands = [
        'Royal Canin',
        'Arden Grange', 
        'Barking Heads',
        'Bosch',
        'Belcando',
        'Pro Plan',
        'Millies Wolfheart',
        'Iams',
        'Specific',
        'Gain'
    ]
    
    for brand in key_brands:
        count = len(df[df['brand'] == brand])
        if count > 0:
            print(f"   ✅ {brand}: {count} products")
        else:
            print(f"   ❌ {brand}: NOT FOUND")

if __name__ == "__main__":
    main()