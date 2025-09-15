#!/usr/bin/env python3
"""
Test improved patterns on the URLs that failed
"""

import sys
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

# URLs that failed (excluding the ones that redirect to category pages)
test_urls = [
    {"name": "Wolf of Wilderness Senior", "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_red/1958908"},
    {"name": "Wolf of Wilderness Single", "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_adult_single_protein/2155922"}
]

print("🧪 TESTING IMPROVED PATTERNS ON FAILED URLS")
print("="*60)

# Create scraper
scraper = OrchestratedScraper('pattern_test', 'gb', 5, 10, len(test_urls), 0)

success_count = 0

for i, product in enumerate(test_urls, 1):
    print(f"\n[{i}/{len(test_urls)}] {product['name']}")
    print(f"URL: {product['url']}")
    print("-" * 50)
    
    # Test scraping
    result = scraper.scrape_product(product['url'])
    
    # Show results
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
    elif 'ingredients_raw' in result:
        print("✅ SUCCESS! Ingredients extracted:")
        print(f"   {result['ingredients_raw'][:80]}...")
        success_count += 1
        
        if 'nutrition' in result:
            print(f"✅ Nutrition: {len(result['nutrition'])} values")
    else:
        print("❌ No ingredients extracted")
        if 'nutrition' in result:
            print(f"✅ Nutrition: {len(result['nutrition'])} values")

print("\n" + "="*60)
print("SUMMARY:")
print(f"  Successful extractions: {success_count}/{len(test_urls)} ({success_count/len(test_urls)*100:.1f}%)")

if success_count == len(test_urls):
    print("🎉 ALL TESTS PASSED! Pattern improvements are working!")
elif success_count > 0:
    print("✅ Some improvements working - ready for broader testing!")
else:
    print("⚠️  No improvements detected")