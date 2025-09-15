#!/usr/bin/env python3
"""
Rescrape the 20 test products with improved patterns to verify >95% accuracy
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import storage

# Add scripts to path
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

load_dotenv()

GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# The 20 products from our test
test_products = [
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/purizon/trial_packs/1191314", "name": "Purizon Grain-free Trial Packs"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_vet_diet/1949350", "name": "Royal Canin Expert Neutered"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/advance_vet_diets/2159368", "name": "Advance Hypoallergenic Mini"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/belcando/baseline/2176816", "name": "Belcando Baseline Young"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bosch/bosch_adult/323020", "name": "Bosch Adult Mini Poultry"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bosch/bosch_senior/317406", "name": "Bosch Adult Mini Senior"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bosch/bosch_adult/1995623", "name": "Bosch HPC Adult Vegan"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bosch/bosch_life_protection/136396", "name": "Bosch Senior Age & Weight"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_dog_food/1488611", "name": "Bozita Grain Free Salmon"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/purizon/single_meat/2124227", "name": "Purizon Single Meat Beef"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_breed/french_bulldog/209128", "name": "Royal Canin French Bulldog"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/royal_canin_care_nutrition/296052", "name": "Royal Canin Medium Sterilised"},
    {"url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_red/1958908", "name": "Wolf of Wilderness Senior"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/farmina/farmina_nd_puppy/1852834", "name": "Farmina N&D Pumpkin"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bosch/bosch_soft/1942621", "name": "Bosch HPC Soft Maxi"},
    {"url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_adult_single_protein/2155922", "name": "Wolf of Wilderness Single"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/bozita/bozita_puppy_junior/2180468", "name": "Bozita Robur Puppy"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/advance/advance_medium/1848", "name": "Advance Medium Adult"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/brit_care/brit_care_adult/2178624", "name": "Brit Care Adult Large"},
    {"url": "https://www.zooplus.com/shop/dogs/dry_dog_food/lukullus/lukullus_cold_pressed/1919268", "name": "Lukullus Cold Pressed"}
]

print("🔄 RESCRAPING 20 TEST PRODUCTS WITH IMPROVED PATTERNS")
print("="*60)
print(f"Target: >95% ingredients extraction accuracy")
print()

# Create scraper
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
session_id = f"rescrape_test_{timestamp}"
gcs_folder = f"scraped/zooplus/{session_id}"

scraper = OrchestratedScraper('rescrape_test', 'gb', 10, 15, 20, 0)

# Initialize GCS
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

results = []
with_ingredients = 0
with_nutrition = 0
errors = 0

for i, product in enumerate(test_products[:20], 1):
    print(f"[{i}/20] {product['name'][:40]}...")
    
    # Scrape product
    result = scraper.scrape_product(product['url'])
    
    # Check results
    has_ingredients = 'ingredients_raw' in result
    has_nutrition = 'nutrition' in result
    has_error = 'error' in result
    
    if has_error:
        print(f"  ❌ Error: {result['error']}")
        errors += 1
    else:
        if has_ingredients:
            print(f"  ✅ Ingredients: {result['ingredients_raw'][:80]}...")
            with_ingredients += 1
        else:
            print(f"  ❌ No ingredients found")
        
        if has_nutrition:
            print(f"  ✅ Nutrition: {len(result['nutrition'])} values")
            with_nutrition += 1
        else:
            print(f"  ❌ No nutrition found")
    
    results.append({
        'name': product['name'],
        'url': product['url'],
        'has_ingredients': has_ingredients,
        'has_nutrition': has_nutrition,
        'has_error': has_error
    })
    
    # Save to GCS
    if not has_error:
        try:
            filename = f"{gcs_folder}/{product['name'].replace(' ', '_').replace('/', '_')}.json"
            blob = bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(result, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
        except Exception as e:
            print(f"    GCS error: {str(e)[:100]}")
    
    # Delay between requests
    if i < 20:
        delay = random.uniform(10, 15)
        print(f"  Waiting {delay:.1f}s...")
        time.sleep(delay)

# Final analysis
print("\n" + "="*60)
print("📊 FINAL RESULTS")
print("="*60)

successful = 20 - errors
print(f"\nScraping:")
print(f"  Successful: {successful}/20 ({successful/20*100:.1f}%)")
print(f"  Errors: {errors}/20")

if successful > 0:
    print(f"\nExtraction (of successful scrapes):")
    print(f"  Ingredients: {with_ingredients}/{successful} ({with_ingredients/successful*100:.1f}%)")
    print(f"  Nutrition: {with_nutrition}/{successful} ({with_nutrition/successful*100:.1f}%)")

print(f"\nOverall:")
print(f"  Ingredients: {with_ingredients}/20 ({with_ingredients/20*100:.1f}%)")
print(f"  Nutrition: {with_nutrition}/20 ({with_nutrition/20*100:.1f}%)")

# List products still missing ingredients
missing_ingredients = [r for r in results if not r['has_ingredients'] and not r['has_error']]
if missing_ingredients:
    print(f"\n⚠️ {len(missing_ingredients)} products still missing ingredients:")
    for r in missing_ingredients[:5]:
        print(f"  - {r['name']}")

# Decision
print("\n" + "-"*60)
print("💡 ACCURACY ASSESSMENT:")

if successful > 0:
    accuracy = with_ingredients / successful * 100
    if accuracy >= 95:
        print(f"  ✅ EXCELLENT! {accuracy:.1f}% accuracy - READY FOR AUTOMATION")
        print("  → The improved patterns are working perfectly!")
    elif accuracy >= 80:
        print(f"  ✅ VERY GOOD! {accuracy:.1f}% accuracy")
        print("  → Significant improvement, consider automation")
    elif accuracy >= 60:
        print(f"  ⚠️ GOOD: {accuracy:.1f}% accuracy")
        print("  → Better but may need more pattern refinement")
    else:
        print(f"  ❌ NEEDS WORK: {accuracy:.1f}% accuracy")
        print("  → Patterns need further improvement")

# Save results
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
with open(f'data/rescrape_test_results_{timestamp}.json', 'w') as f:
    json.dump({
        'timestamp': timestamp,
        'session_id': session_id,
        'total': 20,
        'successful': successful,
        'with_ingredients': with_ingredients,
        'with_nutrition': with_nutrition,
        'accuracy': with_ingredients / successful * 100 if successful > 0 else 0,
        'results': results
    }, f, indent=2)

print(f"\n💾 Results saved to data/rescrape_test_results_{timestamp}.json")
print(f"📁 Scraped files in: gs://{GCS_BUCKET}/{gcs_folder}/")