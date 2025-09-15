#!/usr/bin/env python3
"""
Analyze products without ingredients by brand and identify patterns
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict
import json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def analyze_problem_brands():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all Zooplus products without ingredients
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, brand, product_url, protein_percent'
    ).ilike('product_url', '%zooplus.com%')\
    .is_('ingredients_raw', 'null')\
    .execute()
    
    products = response.data if response.data else []
    print(f"Total products without ingredients: {len(products)}")
    
    # Group by brand
    brands = defaultdict(list)
    for product in products:
        brand = product.get('brand', 'Unknown')
        brands[brand].append(product)
    
    # Sort brands by count
    sorted_brands = sorted(brands.items(), key=lambda x: len(x[1]), reverse=True)
    
    print("\n=== TOP BRANDS WITHOUT INGREDIENTS ===")
    for brand, brand_products in sorted_brands[:10]:
        # Check how many have nutrition
        with_nutrition = sum(1 for p in brand_products if p.get('protein_percent'))
        print(f"\n{brand}: {len(brand_products)} products")
        print(f"  - With nutrition: {with_nutrition}/{len(brand_products)}")
        
        # Show product name patterns
        name_patterns = defaultdict(int)
        for p in brand_products:
            name = p['product_name'].lower()
            if 'trial' in name or 'sample' in name:
                name_patterns['trial/sample'] += 1
            elif 'multipack' in name or 'saver' in name or 'multi buy' in name:
                name_patterns['multipack'] += 1
            elif 'wet' in name or 'pouch' in name or 'tin' in name or 'can' in name:
                name_patterns['wet food'] += 1
            elif 'dry' in name or 'kibble' in name:
                name_patterns['dry food'] += 1
            else:
                name_patterns['other'] += 1
        
        for pattern, count in sorted(name_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {pattern}: {count}")
        
        # Show first 3 URLs for manual inspection
        print(f"  Sample URLs:")
        for p in brand_products[:3]:
            print(f"    - {p['product_url']}")
    
    # Analyze specific problematic brands
    print("\n=== DETAILED BRAND ANALYSIS ===")
    
    problem_brands = ['Lukullus', 'Farmina N&D', 'Rinti', 'MAC\'s']
    
    for brand_name in problem_brands:
        if brand_name in brands:
            print(f"\n{brand_name}:")
            brand_products = brands[brand_name]
            
            # Group by product line
            product_lines = defaultdict(list)
            for p in brand_products:
                # Extract product line from name
                name_parts = p['product_name'].split(' - ')
                if len(name_parts) > 1:
                    line = name_parts[0]
                else:
                    line = p['product_name'].split(',')[0] if ',' in p['product_name'] else p['product_name'][:30]
                product_lines[line].append(p)
            
            for line, line_products in sorted(product_lines.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                print(f"  {line}: {len(line_products)} products")
                # Show one URL
                if line_products:
                    print(f"    URL: {line_products[0]['product_url']}")

if __name__ == "__main__":
    analyze_problem_brands()