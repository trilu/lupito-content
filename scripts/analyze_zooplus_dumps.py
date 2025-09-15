#!/usr/bin/env python3
"""
Analyze Zooplus data dumps and compare with database
"""

import pandas as pd
import os
import re
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def extract_brand_from_url(url):
    """Extract brand from Zooplus URL structure"""
    if pd.isna(url):
        return None
    # Pattern: /shop/dogs/[category]/[brand]/
    match = re.search(r'/shop/dogs/[^/]+/([^/]+)/', url)
    if match:
        brand = match.group(1).replace('_', ' ').title()
        # Common brand mappings
        brand_map = {
            'Wolf Of Wilderness': 'Wolf of Wilderness',
            'Hills Science Plan': "Hill's Science Plan",
            'Hills Prescription Diet': "Hill's Prescription Diet",
            'Royal Canin Vet Diet': 'Royal Canin Veterinary Diet',
            'Royal Canin Care Nutrition': 'Royal Canin Care Nutrition',
            'Purina Pro Plan': 'Pro Plan',
            'Concept For Life': 'Concept for Life'
        }
        return brand_map.get(brand, brand)
    return None

def analyze_file(filepath, file_desc):
    """Analyze a single Zooplus CSV file"""
    print(f"\n📄 Analyzing {file_desc}: {filepath}")
    print("=" * 60)
    
    # Read CSV
    df = pd.read_csv(filepath)
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Identify key columns
    url_col = None
    name_col = None
    desc_col = None
    
    for col in df.columns:
        if 'href' in col.lower():
            url_col = col
        if 'product_name' in col.lower() or col == 'text-1':
            name_col = col
        if 'description' in col.lower() or col == 'text-2':
            desc_col = col
    
    print(f"\nIdentified columns:")
    print(f"  URL: {url_col}")
    print(f"  Name: {name_col}")
    print(f"  Description: {desc_col}")
    
    if not url_col:
        print("⚠️ No URL column found")
        return None
    
    # Extract product data
    products = []
    for _, row in df.iterrows():
        url = row.get(url_col)
        if pd.isna(url) or not url:
            continue
            
        # Extract brand from URL
        brand = extract_brand_from_url(url)
        
        # Extract product name
        product_name = row.get(name_col, '') if name_col else ''
        if pd.isna(product_name):
            product_name = ''
        
        # Check for ingredients/nutrition in description
        description = row.get(desc_col, '') if desc_col else ''
        if pd.isna(description):
            description = ''
        
        has_ingredients = False
        has_nutrition = False
        
        if description:
            # Check for ingredient keywords
            if any(word in description.lower() for word in ['ingredient', 'composition', 'meat', 'protein', 'rice', 'vegetable']):
                has_ingredients = True
            
            # Check for nutrition keywords
            if any(word in description.lower() for word in ['protein:', 'fat:', 'fibre:', 'ash:', 'moisture:', 'analytical']):
                has_nutrition = True
        
        # Determine if wet or dry
        food_type = 'unknown'
        if 'dry_dog_food' in url:
            food_type = 'dry'
        elif 'canned_dog_food' in url or 'wet_dog_food' in url:
            food_type = 'wet'
        
        products.append({
            'url': url,
            'brand': brand,
            'product_name': str(product_name),
            'has_ingredients': has_ingredients,
            'has_nutrition': has_nutrition,
            'food_type': food_type,
            'description_length': len(str(description))
        })
    
    products_df = pd.DataFrame(products)
    
    # Statistics
    print(f"\n📊 Product Statistics:")
    print(f"  Total products with URLs: {len(products_df)}")
    print(f"  Unique brands: {products_df['brand'].nunique()}")
    print(f"  Products with ingredients: {products_df['has_ingredients'].sum()}")
    print(f"  Products with nutrition: {products_df['has_nutrition'].sum()}")
    
    # Food type breakdown
    print(f"\n🍖 Food Type Breakdown:")
    for food_type, count in products_df['food_type'].value_counts().items():
        print(f"  {food_type}: {count}")
    
    # Top brands
    print(f"\n🏷️ Top 10 Brands:")
    for brand, count in products_df['brand'].value_counts().head(10).items():
        print(f"  {brand}: {count} products")
    
    return products_df

def compare_with_database(products_df):
    """Compare products with existing database"""
    print("\n🔄 Comparing with Database")
    print("=" * 60)
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all products from database
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, brand, product_url, ingredients_raw'
    ).execute()
    
    db_products = pd.DataFrame(response.data)
    print(f"Database products: {len(db_products)}")
    
    # Products with Zooplus URLs
    db_zooplus = db_products[db_products['product_url'].str.contains('zooplus', na=False)]
    print(f"Database products with Zooplus URLs: {len(db_zooplus)}")
    
    # Products without ingredients
    db_no_ingredients = db_products[db_products['ingredients_raw'].isna()]
    print(f"Database products without ingredients: {len(db_no_ingredients)}")
    
    # Match products
    matches = {
        'exact_url_match': 0,
        'new_products': 0,
        'update_candidates': 0,
        'scrape_candidates': 0
    }
    
    new_products = []
    update_candidates = []
    scrape_candidates = []
    
    for _, product in products_df.iterrows():
        url = product['url']
        brand = product['brand']
        name = product['product_name']
        
        # Check if URL exists in database
        existing = db_products[db_products['product_url'] == url]
        
        if len(existing) > 0:
            matches['exact_url_match'] += 1
            
            # Check if needs ingredients
            if existing.iloc[0]['ingredients_raw'] is None or pd.isna(existing.iloc[0]['ingredients_raw']):
                if product['has_ingredients'] or product['has_nutrition']:
                    update_candidates.append({
                        'product_key': existing.iloc[0]['product_key'],
                        'url': url,
                        'brand': brand,
                        'name': name,
                        'has_ingredients': product['has_ingredients'],
                        'has_nutrition': product['has_nutrition']
                    })
                    matches['update_candidates'] += 1
                else:
                    scrape_candidates.append({
                        'product_key': existing.iloc[0]['product_key'],
                        'url': url,
                        'brand': brand,
                        'name': name
                    })
                    matches['scrape_candidates'] += 1
        else:
            # New product
            new_products.append({
                'url': url,
                'brand': brand,
                'name': name,
                'has_ingredients': product['has_ingredients'],
                'has_nutrition': product['has_nutrition'],
                'food_type': product['food_type']
            })
            matches['new_products'] += 1
    
    print(f"\n🎯 Match Results:")
    print(f"  Exact URL matches: {matches['exact_url_match']}")
    print(f"  New products to add: {matches['new_products']}")
    print(f"  Products to update (have data): {matches['update_candidates']}")
    print(f"  Products to scrape (need data): {matches['scrape_candidates']}")
    
    return {
        'new_products': pd.DataFrame(new_products),
        'update_candidates': pd.DataFrame(update_candidates),
        'scrape_candidates': pd.DataFrame(scrape_candidates),
        'stats': matches
    }

def main():
    print("🔍 ZOOPLUS DATA DUMP ANALYSIS")
    print("=" * 80)
    
    # Analyze both files
    file1 = "data/zooplus/zooplus-com-2025-09-12.csv"
    file2 = "data/zooplus/zooplus-com-2025-09-12-2.csv"
    
    df1 = analyze_file(file1, "File 1 (Mixed/Wet)")
    df2 = analyze_file(file2, "File 2 (Dry)")
    
    # Combine products
    if df1 is not None and df2 is not None:
        combined_df = pd.concat([df1, df2], ignore_index=True)
        
        # Remove duplicates based on URL
        combined_df = combined_df.drop_duplicates(subset=['url'])
        
        print("\n📊 COMBINED STATISTICS")
        print("=" * 60)
        print(f"Total unique products: {len(combined_df)}")
        print(f"Unique brands: {combined_df['brand'].nunique()}")
        print(f"With ingredients: {combined_df['has_ingredients'].sum()}")
        print(f"With nutrition: {combined_df['has_nutrition'].sum()}")
        
        # Compare with database
        comparison = compare_with_database(combined_df)
        
        # Summary
        print("\n📋 FINAL SUMMARY")
        print("=" * 60)
        print(f"New products to import: {len(comparison['new_products'])}")
        print(f"Products to update with data: {len(comparison['update_candidates'])}")
        print(f"Products to scrape: {len(comparison['scrape_candidates'])}")
        
        # Save results
        comparison['new_products'].to_csv('data/zooplus_new_products.csv', index=False)
        comparison['update_candidates'].to_csv('data/zooplus_update_candidates.csv', index=False)
        comparison['scrape_candidates'].to_csv('data/zooplus_scrape_candidates.csv', index=False)
        
        print("\n💾 Results saved to:")
        print("  - data/zooplus_new_products.csv")
        print("  - data/zooplus_update_candidates.csv")
        print("  - data/zooplus_scrape_candidates.csv")

if __name__ == "__main__":
    main()
