#!/usr/bin/env python3
"""
Analyze gaps in ingredient coverage to identify priority brands and products
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def analyze_gaps():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("🔍 ANALYZING GAPS IN INGREDIENT COVERAGE")
    print("=" * 60)
    
    # Get products without ingredients
    response = supabase.table('foods_canonical').select(
        'brand, product_name, product_url'
    ).is_('ingredients_raw', 'null').execute()
    
    products_without_ingredients = response.data
    
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Products without ingredients: {len(products_without_ingredients):,}")
    
    # Analyze by brand
    brand_gaps = defaultdict(lambda: {'count': 0, 'has_zooplus': 0, 'sources': set()})
    source_gaps = defaultdict(int)
    
    for product in products_without_ingredients:
        brand = product['brand'] or 'Unknown'
        url = product['product_url'] or ''
        
        # Determine source from URL
        source = 'Unknown'
        if url:
            if 'zooplus' in url.lower():
                source = 'Zooplus'
            elif 'chewy' in url.lower():
                source = 'Chewy'
            elif 'petfoodexpert' in url.lower():
                source = 'PetFoodExpert'
            elif 'aadf' in url.lower():
                source = 'AADF'
            else:
                source = 'Other'
        
        brand_gaps[brand]['count'] += 1
        brand_gaps[brand]['sources'].add(source)
        if 'zooplus' in url.lower():
            brand_gaps[brand]['has_zooplus'] += 1
        
        source_gaps[source] += 1
    
    # Sort brands by gap size
    sorted_brands = sorted(brand_gaps.items(), key=lambda x: x[1]['count'], reverse=True)
    
    print(f"\n🏷️ TOP 20 BRANDS NEEDING INGREDIENTS:")
    print(f"{'Brand':<30} {'Missing':<10} {'Has Zooplus':<15} {'Sources'}")
    print("-" * 80)
    
    for brand, info in sorted_brands[:20]:
        sources_str = ', '.join(sorted(info['sources']))[:30]
        print(f"{brand[:29]:<30} {info['count']:<10} {info['has_zooplus']:<15} {sources_str}")
    
    # Analyze by source
    print(f"\n🛒 GAPS BY SOURCE:")
    print(f"{'Source':<25} {'Missing Products'}")
    print("-" * 45)
    
    for source, count in sorted(source_gaps.items(), key=lambda x: x[1], reverse=True):
        print(f"{source[:24]:<25} {count:,}")
    
    # Check products with Zooplus URLs but no ingredients
    zooplus_without_ingredients = [
        p for p in products_without_ingredients 
        if p['product_url'] and 'zooplus' in p['product_url'].lower()
    ]
    
    print(f"\n🎯 ZOOPLUS OPPORTUNITIES:")
    print(f"   Products with Zooplus URLs but no ingredients: {len(zooplus_without_ingredients):,}")
    
    if zooplus_without_ingredients:
        # Group by brand
        zooplus_brands = defaultdict(int)
        for p in zooplus_without_ingredients:
            zooplus_brands[p['brand'] or 'Unknown'] += 1
        
        print(f"\n   Top brands to scrape from Zooplus:")
        for brand, count in sorted(zooplus_brands.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   - {brand}: {count} products")
    
    # Products without any URL
    no_url_products = [
        p for p in products_without_ingredients 
        if not p['product_url']
    ]
    
    print(f"\n⚠️ PRODUCTS WITHOUT URLs:")
    print(f"   Count: {len(no_url_products):,}")
    
    if no_url_products:
        no_url_brands = defaultdict(int)
        for p in no_url_products:
            no_url_brands[p['brand'] or 'Unknown'] += 1
        
        print(f"\n   Top brands without URLs:")
        for brand, count in sorted(no_url_brands.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {brand}: {count} products")
    
    # Calculate potential coverage improvement
    print(f"\n📈 COVERAGE IMPROVEMENT POTENTIAL:")
    
    # If we scrape all Zooplus URLs
    current_with_ingredients = 3202  # From status check
    potential_with_zooplus = current_with_ingredients + len(zooplus_without_ingredients)
    potential_percentage = (potential_with_zooplus / 8190) * 100
    
    print(f"   Current coverage: {current_with_ingredients:,}/8,190 ({(current_with_ingredients/8190)*100:.1f}%)")
    print(f"   If all Zooplus scraped: {potential_with_zooplus:,}/8,190 ({potential_percentage:.1f}%)")
    print(f"   Improvement: +{len(zooplus_without_ingredients):,} products (+{potential_percentage - 39.1:.1f}%)")
    
    return products_without_ingredients, sorted_brands

if __name__ == "__main__":
    products, brands = analyze_gaps()
