#!/usr/bin/env python3
"""
Test scraping on specific problematic brands to identify page structure differences
"""

import os
import sys
import time
import random
from dotenv import load_dotenv
from supabase import create_client

# Add scripts to path
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def test_problem_brands():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Test URLs from problematic brands
    test_products = [
        # Lukullus - different product types
        {
            'brand': 'Lukullus', 
            'type': 'canned_senior',
            'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/lukullus/lukullus_senior/1343803?activeVariant=1343803.1',
            'product_key': 'zooplus.com|1343803.1'
        },
        {
            'brand': 'Lukullus',
            'type': 'dry_cold_pressed', 
            'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/lukullus/adult/1903425',
            'product_key': 'zooplus.com|1903425'
        },
        
        # Farmina N&D
        {
            'brand': 'Farmina N&D',
            'type': 'ocean_dry',
            'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/farmina/ocean/1584191?activeVariant=1584191.0',
            'product_key': 'zooplus.com|1584191.0'
        },
        {
            'brand': 'Farmina N&D',
            'type': 'pumpkin_dry',
            'url': 'https://www.zooplus.com/shop/dogs/dry_dog_food/farmina/pumpkin/1584188?activeVariant=1584188.0',
            'product_key': 'zooplus.com|1584188.0'
        },
        
        # Rinti
        {
            'brand': 'Rinti',
            'type': 'single_meat',
            'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/1949631?activeVariant=1949631.0',
            'product_key': 'zooplus.com|1949631.0'
        },
        {
            'brand': 'Rinti',
            'type': 'sensible',
            'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/rinti_sensible/568066?activeVariant=568066.6',
            'product_key': 'zooplus.com|568066.6'
        },
        
        # Rocco
        {
            'brand': 'Rocco',
            'type': 'classic',
            'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/rocco/rocco_classic/154458?activeVariant=154458.23',
            'product_key': 'zooplus.com|154458.23'
        },
        
        # Wolf of Wilderness
        {
            'brand': 'Wolf Of Wilderness',
            'type': 'wet_food',
            'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/hundenassfuttermitdreifachenproteinenregionen/1952494?activeVariant=1952494.0',
            'product_key': 'zooplus.com|1952494.0'
        },
        
        # MAC's insect protein
        {
            'brand': "MAC's",
            'type': 'insect_protein',
            'url': 'https://www.zooplus.com/shop/dogs/canned_dog_food/macs/2029471?activeVariant=2029471.0',
            'product_key': 'zooplus.com|2029471.0'
        }
    ]
    
    # Create scraper
    scraper = OrchestratedScraper('test_brands', 'gb', 10, 15, 10, 0)
    
    print("=" * 80)
    print("TESTING PROBLEMATIC BRANDS")
    print("=" * 80)
    
    results = []
    
    for i, product in enumerate(test_products, 1):
        print(f"\n[{i}/{len(test_products)}] Testing {product['brand']} ({product['type']})")
        print(f"URL: {product['url']}")
        
        # Add delay except for first request
        if i > 1:
            delay = random.uniform(10, 15)
            print(f"Waiting {delay:.1f}s...")
            time.sleep(delay)
        
        # Scrape
        result = scraper.scrape_product(product['url'])
        
        # Analyze result
        analysis = {
            'brand': product['brand'],
            'type': product['type'],
            'url': product['url'],
            'has_ingredients': False,
            'has_nutrition': False,
            'error': None,
            'ingredients_preview': None,
            'page_length': 0
        }
        
        if 'error' in result:
            analysis['error'] = result['error']
            print(f"  ❌ Error: {result['error']}")
        else:
            # Check what was extracted
            if 'page_text' in result:
                analysis['page_length'] = len(result['page_text'])
                print(f"  Page text length: {analysis['page_length']} chars")
                
                # Show snippet around "Ingredients" if present
                text = result['page_text']
                if 'Ingredients' in text:
                    idx = text.find('Ingredients')
                    snippet = text[max(0, idx-100):min(len(text), idx+500)]
                    print(f"  Context around 'Ingredients':")
                    print(f"    {snippet}")
            
            if 'ingredients_raw' in result and result['ingredients_raw']:
                analysis['has_ingredients'] = True
                analysis['ingredients_preview'] = result['ingredients_raw'][:100]
                print(f"  ✅ Ingredients found: {analysis['ingredients_preview']}...")
            else:
                print(f"  ⚠️  No ingredients extracted")
            
            if 'nutrition' in result and result['nutrition']:
                analysis['has_nutrition'] = True
                print(f"  ✅ Nutrition found: {len(result['nutrition'])} values")
            else:
                print(f"  ⚠️  No nutrition extracted")
        
        results.append(analysis)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Group by brand
    brands_summary = {}
    for r in results:
        brand = r['brand']
        if brand not in brands_summary:
            brands_summary[brand] = {'total': 0, 'with_ingredients': 0, 'with_nutrition': 0, 'errors': 0}
        
        brands_summary[brand]['total'] += 1
        if r['has_ingredients']:
            brands_summary[brand]['with_ingredients'] += 1
        if r['has_nutrition']:
            brands_summary[brand]['with_nutrition'] += 1
        if r['error']:
            brands_summary[brand]['errors'] += 1
    
    for brand, stats in brands_summary.items():
        print(f"\n{brand}:")
        print(f"  Total tested: {stats['total']}")
        print(f"  With ingredients: {stats['with_ingredients']}/{stats['total']} ({stats['with_ingredients']/stats['total']*100:.0f}%)")
        print(f"  With nutrition: {stats['with_nutrition']}/{stats['total']} ({stats['with_nutrition']/stats['total']*100:.0f}%)")
        if stats['errors'] > 0:
            print(f"  Errors: {stats['errors']}")
    
    # Overall stats
    total = len(results)
    with_ingredients = sum(1 for r in results if r['has_ingredients'])
    with_nutrition = sum(1 for r in results if r['has_nutrition'])
    errors = sum(1 for r in results if r['error'])
    
    print(f"\nOVERALL:")
    print(f"  Total tested: {total}")
    print(f"  With ingredients: {with_ingredients}/{total} ({with_ingredients/total*100:.1f}%)")
    print(f"  With nutrition: {with_nutrition}/{total} ({with_nutrition/total*100:.1f}%)")
    print(f"  Errors: {errors}")
    
    return results

if __name__ == "__main__":
    test_problem_brands()