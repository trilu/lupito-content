#!/usr/bin/env python3
"""
Test specific URLs with updated patterns
"""

import sys
import time
import random

sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

# URLs that previously failed
test_urls = [
    'https://www.zooplus.com/shop/dogs/canned_dog_food/lukullus/lukullus_senior/1343803?activeVariant=1343803.1',
    'https://www.zooplus.com/shop/dogs/dry_dog_food/lukullus/adult/1903425',
    'https://www.zooplus.com/shop/dogs/dry_dog_food/farmina/ocean/1584191?activeVariant=1584191.0',
    'https://www.zooplus.com/shop/dogs/dry_dog_food/farmina/pumpkin/1584188?activeVariant=1584188.0',
    'https://www.zooplus.com/shop/dogs/canned_dog_food/rinti/1949631?activeVariant=1949631.0'
]

scraper = OrchestratedScraper('url_test', 'gb', 10, 15, 1, 0)

print("=" * 80)
print("TESTING SPECIFIC URLS WITH UPDATED PATTERNS")
print("=" * 80)

success_count = 0
total_count = len(test_urls)

for i, url in enumerate(test_urls, 1):
    print(f"\n[{i}/{total_count}] Testing: {url}")
    
    # Add delay except for first
    if i > 1:
        delay = random.uniform(10, 15)
        print(f"  Waiting {delay:.1f}s...")
        time.sleep(delay)
    
    result = scraper.scrape_product(url)
    
    if 'error' in result:
        print(f"  ❌ Error: {result['error']}")
    else:
        if 'ingredients_raw' in result:
            print(f"  ✅ INGREDIENTS FOUND!")
            print(f"     Preview: {result['ingredients_raw'][:150]}...")
            success_count += 1
        else:
            print(f"  ⚠️  No ingredients found")
        
        if 'nutrition' in result and result['nutrition']:
            print(f"  ✅ Nutrition: {len(result['nutrition'])} values")

print("\n" + "=" * 80)
print(f"RESULTS: {success_count}/{total_count} URLs extracted ingredients successfully")
print(f"Success rate: {success_count/total_count*100:.1f}%")
print("=" * 80)