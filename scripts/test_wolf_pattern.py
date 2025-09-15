#!/usr/bin/env python3
"""
Test the new pattern on Wolf of Wilderness Senior page
"""

import sys
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

# Test the Wolf of Wilderness page that was failing
url = "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_red/1958908"

print("🧪 TESTING NEW PATTERN ON WOLF OF WILDERNESS")
print("="*60)
print(f"URL: {url}")
print()

# Create scraper  
scraper = OrchestratedScraper('pattern_test', 'gb', 10, 15, 1, 0)

# Test scraping
result = scraper.scrape_product(url)

# Show results
if 'error' in result:
    print(f"❌ Error: {result['error']}")
elif 'ingredients_raw' in result:
    print("✅ SUCCESS! Ingredients extracted:")
    print(f"   {result['ingredients_raw'][:100]}...")
    print()
    if 'nutrition' in result:
        print(f"✅ Nutrition extracted: {len(result['nutrition'])} values")
        for key, value in result['nutrition'].items():
            print(f"   {key}: {value}%")
else:
    print("❌ No ingredients extracted")
    if 'nutrition' in result:
        print(f"✅ Nutrition extracted: {len(result['nutrition'])} values")