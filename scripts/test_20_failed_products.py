#!/usr/bin/env python3
"""
Test updated patterns on 20 products that are still missing ingredients
"""

import os
import sys
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Add scripts to path
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def test_failed_products():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get 20 products still missing ingredients (mix of brands)
    response = supabase.table('foods_canonical').select(
        'product_key, product_name, brand, product_url, protein_percent'
    ).ilike('product_url', '%zooplus.com%')\
    .is_('ingredients_raw', 'null')\
    .not_.ilike('product_name', '%trial%pack%')\
    .not_.ilike('product_name', '%sample%')\
    .limit(20)\
    .execute()
    
    products = response.data if response.data else []
    
    print("=" * 80)
    print(f"TESTING {len(products)} FAILED PRODUCTS WITH UPDATED PATTERNS")
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Create scraper
    scraper = OrchestratedScraper('test_failed_20', 'gb', 12, 18, 20, 0)
    
    results = {
        'total': len(products),
        'scraped': 0,
        'with_ingredients': 0,
        'with_nutrition': 0,
        'errors': 0
    }
    
    # Test each product
    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {product['brand']}: {product['product_name'][:50]}...")
        print(f"  URL: {product['product_url']}")
        
        # Has nutrition?
        if product.get('protein_percent'):
            print(f"  Has nutrition: YES (protein: {product['protein_percent']}%)")
        else:
            print(f"  Has nutrition: NO")
        
        # Add delay except for first request
        if i > 1:
            delay = random.uniform(12, 18)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)
        
        # Scrape
        print(f"  Scraping...")
        result = scraper.scrape_product(product['product_url'])
        
        # Check results
        if 'error' in result:
            print(f"  ❌ Error: {result['error']}")
            results['errors'] += 1
        else:
            results['scraped'] += 1
            
            if 'ingredients_raw' in result and result['ingredients_raw']:
                print(f"  ✅ INGREDIENTS FOUND!")
                print(f"     Preview: {result['ingredients_raw'][:150]}...")
                results['with_ingredients'] += 1
            else:
                print(f"  ⚠️  No ingredients extracted")
                # Show page text around "Ingredients" if present
                if 'page_text' in result and 'Ingredients' in result['page_text']:
                    text = result['page_text']
                    idx = text.find('Ingredients')
                    if idx > 0:
                        snippet = text[max(0, idx-50):min(len(text), idx+300)]
                        print(f"  Debug - Text around 'Ingredients':")
                        print(f"    {repr(snippet)}")
            
            if 'nutrition' in result and result['nutrition']:
                print(f"  ✅ Nutrition: {len(result['nutrition'])} values")
                results['with_nutrition'] += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total products tested: {results['total']}")
    print(f"Successfully scraped: {results['scraped']}")
    print(f"With ingredients: {results['with_ingredients']}/{results['scraped']} ({results['with_ingredients']/results['scraped']*100:.1f}% of scraped)")
    print(f"With nutrition: {results['with_nutrition']}/{results['scraped']}")
    print(f"Errors: {results['errors']}")
    
    if results['scraped'] > 0:
        extraction_rate = results['with_ingredients'] / results['scraped'] * 100
        print(f"\n🎯 EXTRACTION RATE: {extraction_rate:.1f}%")
        
        if extraction_rate >= 90:
            print("✅ EXCELLENT! Ready for full-scale rescraping")
        elif extraction_rate >= 70:
            print("⚠️  GOOD but could be improved")
        else:
            print("❌ NEEDS MORE PATTERN IMPROVEMENTS")
    
    print(f"\nTest completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_failed_products()