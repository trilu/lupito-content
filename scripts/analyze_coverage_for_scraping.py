#!/usr/bin/env python3
"""
Analyze database coverage to plan smart scraping strategy
Focus on reaching 95% coverage for ingredients and nutrition
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from collections import defaultdict

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def analyze_coverage():
    """Analyze current coverage and identify scraping priorities"""
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("ANALYZING DATABASE COVERAGE FOR SCRAPING")
    print("=" * 60)
    
    # Get overall statistics
    print("\n1. OVERALL COVERAGE")
    print("-" * 40)
    
    # Total products
    total_response = supabase.table('foods_canonical').select('*', count='exact').execute()
    total_products = total_response.count
    
    # With ingredients
    ingredients_response = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('ingredients_raw', 'null').execute()
    with_ingredients = ingredients_response.count
    
    # With complete nutrition (protein + fat at minimum)
    nutrition_response = supabase.table('foods_canonical').select('*', count='exact')\
        .not_.is_('protein_percent', 'null')\
        .not_.is_('fat_percent', 'null').execute()
    with_nutrition = nutrition_response.count
    
    ingredients_pct = (with_ingredients / total_products * 100) if total_products > 0 else 0
    nutrition_pct = (with_nutrition / total_products * 100) if total_products > 0 else 0
    
    print(f"Total products: {total_products:,}")
    print(f"With ingredients: {with_ingredients:,} ({ingredients_pct:.1f}%)")
    print(f"With nutrition: {with_nutrition:,} ({nutrition_pct:.1f}%)")
    
    gap_to_95_ingredients = max(0, (total_products * 0.95) - with_ingredients)
    gap_to_95_nutrition = max(0, (total_products * 0.95) - with_nutrition)
    
    print(f"\nTo reach 95% coverage:")
    print(f"  Need ingredients for: {int(gap_to_95_ingredients):,} more products")
    print(f"  Need nutrition for: {int(gap_to_95_nutrition):,} more products")
    
    # Analyze by source
    print("\n2. COVERAGE BY SOURCE")
    print("-" * 40)
    
    sources = ['zooplus', 'chewy', 'petfood-expert', 'aadf']
    
    source_stats = {}
    for source in sources:
        # Get products from this source
        if source == 'aadf':
            source_query = supabase.table('foods_canonical').select('*', count='exact')\
                .ilike('sources', '%aadf%')
        else:
            source_query = supabase.table('foods_canonical').select('*', count='exact')\
                .ilike('product_url', f'%{source}%')
        
        source_total = source_query.execute().count
        
        if source_total > 0:
            # With ingredients
            if source == 'aadf':
                ingr_query = supabase.table('foods_canonical').select('*', count='exact')\
                    .ilike('sources', '%aadf%')\
                    .not_.is_('ingredients_raw', 'null')
            else:
                ingr_query = supabase.table('foods_canonical').select('*', count='exact')\
                    .ilike('product_url', f'%{source}%')\
                    .not_.is_('ingredients_raw', 'null')
            
            source_ingredients = ingr_query.execute().count
            
            # With nutrition
            if source == 'aadf':
                nutr_query = supabase.table('foods_canonical').select('*', count='exact')\
                    .ilike('sources', '%aadf%')\
                    .not_.is_('protein_percent', 'null')
            else:
                nutr_query = supabase.table('foods_canonical').select('*', count='exact')\
                    .ilike('product_url', f'%{source}%')\
                    .not_.is_('protein_percent', 'null')
            
            source_nutrition = nutr_query.execute().count
            
            source_stats[source] = {
                'total': source_total,
                'ingredients': source_ingredients,
                'nutrition': source_nutrition,
                'ingredients_pct': source_ingredients / source_total * 100,
                'nutrition_pct': source_nutrition / source_total * 100,
                'missing_ingredients': source_total - source_ingredients,
                'missing_nutrition': source_total - source_nutrition
            }
    
    # Sort by most missing ingredients
    sorted_sources = sorted(source_stats.items(), 
                           key=lambda x: x[1]['missing_ingredients'], 
                           reverse=True)
    
    for source, stats in sorted_sources:
        if stats['total'] > 0:
            print(f"\n{source.upper()}:")
            print(f"  Total: {stats['total']:,}")
            print(f"  Ingredients: {stats['ingredients']:,}/{stats['total']:,} ({stats['ingredients_pct']:.1f}%)")
            print(f"  Nutrition: {stats['nutrition']:,}/{stats['total']:,} ({stats['nutrition_pct']:.1f}%)")
            print(f"  Missing ingredients: {stats['missing_ingredients']:,}")
            print(f"  Missing nutrition: {stats['missing_nutrition']:,}")
    
    # Get Zooplus products without ingredients (priority)
    print("\n3. SCRAPING PRIORITY: ZOOPLUS")
    print("-" * 40)
    
    zooplus_missing = supabase.table('foods_canonical').select('product_key, product_name, brand')\
        .ilike('product_url', '%zooplus%')\
        .is_('ingredients_raw', 'null')\
        .limit(10).execute()
    
    print(f"Sample products missing ingredients:")
    for p in zooplus_missing.data[:5]:
        print(f"  • {p['brand']}: {p['product_name'][:50]}")
    
    # Calculate scraping plan
    print("\n4. SMART SCRAPING PLAN")
    print("-" * 40)
    
    # Focus on Zooplus first (has the most products)
    zooplus_stats = source_stats.get('zooplus', {})
    if zooplus_stats:
        products_to_scrape = zooplus_stats['missing_ingredients']
        
        # Calculate time with safe delays
        seconds_per_product = 20  # 15-20 second delay + scraping time
        total_seconds = products_to_scrape * seconds_per_product
        hours = total_seconds / 3600
        
        # Batching strategy
        products_per_hour = 3600 / seconds_per_product  # ~180 per hour
        products_per_day = products_per_hour * 8  # 8 hours of scraping per day
        days_needed = products_to_scrape / products_per_day
        
        print(f"Zooplus products to scrape: {products_to_scrape:,}")
        print(f"\nWith 20-second intervals (safe):")
        print(f"  • {int(products_per_hour)} products per hour")
        print(f"  • {int(products_per_day)} products per day (8 hours)")
        print(f"  • {days_needed:.1f} days to complete")
        
        print(f"\nRecommended approach:")
        print(f"  1. Run batches of 50-100 products")
        print(f"  2. Use 15-20 second random delays")
        print(f"  3. Rotate through different times of day")
        print(f"  4. Monitor for rate limiting")
        print(f"  5. Save everything to GCS first")
    
    return {
        'total_products': total_products,
        'current_ingredients_pct': ingredients_pct,
        'current_nutrition_pct': nutrition_pct,
        'gap_to_95_ingredients': int(gap_to_95_ingredients),
        'gap_to_95_nutrition': int(gap_to_95_nutrition),
        'source_stats': source_stats
    }

if __name__ == "__main__":
    stats = analyze_coverage()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Start with Zooplus (largest gap)")
    print("2. Run scraper in batches throughout the day")
    print("3. Monitor GCS for successful scrapes")
    print("4. Process GCS files in bulk")
    print("5. Track progress toward 95% goal")