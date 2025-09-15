#!/usr/bin/env python3
"""
Test improved patterns on 50 products that failed to extract ingredients
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from google.cloud import storage

# Add scripts to path
sys.path.insert(0, 'scripts')
from orchestrated_scraper import OrchestratedScraper

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

print("🔍 GETTING 50 PRODUCTS WITHOUT INGREDIENTS...")
print("="*60)

# Get 50 Zooplus products without ingredients
# Exclude trial packs
response = supabase.table('foods_canonical').select(
    'product_key, product_name, brand, product_url'
).ilike('product_url', '%zooplus.com%')\
.is_('ingredients_raw', 'null')\
.not_.ilike('product_name', '%trial%pack%')\
.not_.ilike('product_name', '%sample%')\
.limit(50).execute()

products = response.data if response.data else []
print(f"Found {len(products)} products without ingredients")

if not products:
    print("No products found to test!")
    sys.exit(0)

# Create session
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
session_id = f"test_50_failed_{timestamp}"
gcs_folder = f"scraped/zooplus/{session_id}"

print(f"\n🧪 TESTING IMPROVED PATTERNS ON 50 FAILED PRODUCTS")
print("="*60)
print(f"Session: {session_id}")
print(f"GCS: gs://{GCS_BUCKET}/{gcs_folder}/")
print()

# Create scraper with improved patterns
scraper = OrchestratedScraper('test_50', 'gb', 10, 15, 50, 0)

results = []
with_ingredients = 0
with_nutrition = 0
errors = 0
wet_food_count = 0
dry_food_count = 0

for i, product in enumerate(products[:50], 1):
    print(f"[{i}/50] {product['brand']}: {product['product_name'][:40]}...")
    
    # Check if wet/canned food
    is_wet = 'canned' in product['product_url'] or 'wet' in product['product_url'].lower()
    if is_wet:
        wet_food_count += 1
    else:
        dry_food_count += 1
    
    # Scrape product
    result = scraper.scrape_product(product['product_url'])
    
    # Check results
    has_ingredients = 'ingredients_raw' in result
    has_nutrition = 'nutrition' in result
    has_error = 'error' in result
    
    if has_error:
        print(f"  ❌ Error: {result['error']}")
        errors += 1
    else:
        if has_ingredients:
            print(f"  ✅ Ingredients found: {result['ingredients_raw'][:80]}...")
            with_ingredients += 1
        else:
            print(f"  ⚠️ No ingredients found")
        
        if has_nutrition:
            print(f"  ✅ Nutrition found: {len(result['nutrition'])} values")
            with_nutrition += 1
        else:
            print(f"  ⚠️ No nutrition found")
    
    results.append({
        'name': product['product_name'],
        'brand': product['brand'],
        'url': product['product_url'],
        'is_wet': is_wet,
        'has_ingredients': has_ingredients,
        'has_nutrition': has_nutrition,
        'has_error': has_error
    })
    
    # Save to GCS
    if not has_error:
        try:
            safe_key = product['product_key'].replace('|', '_').replace('/', '_')
            filename = f"{gcs_folder}/{safe_key}.json"
            blob = bucket.blob(filename)
            blob.upload_from_string(
                json.dumps(result, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
        except Exception as e:
            print(f"    GCS error: {str(e)[:100]}")
    
    # Delay between requests
    if i < 50:
        delay = random.uniform(10, 15)
        print(f"  Waiting {delay:.1f}s...")
        time.sleep(delay)

# Final analysis
print("\n" + "="*60)
print("📊 FINAL RESULTS ANALYSIS")
print("="*60)

successful = 50 - errors
print(f"\nScraping:")
print(f"  Successful: {successful}/50 ({successful/50*100:.1f}%)")
print(f"  Errors: {errors}/50")

print(f"\nProduct Types:")
print(f"  Dry food: {dry_food_count}")
print(f"  Wet/Canned food: {wet_food_count}")

if successful > 0:
    print(f"\nExtraction (of successful scrapes):")
    print(f"  Ingredients: {with_ingredients}/{successful} ({with_ingredients/successful*100:.1f}%)")
    print(f"  Nutrition: {with_nutrition}/{successful} ({with_nutrition/successful*100:.1f}%)")
    
    # Analyze by type
    wet_with_ingr = sum(1 for r in results if r['is_wet'] and r['has_ingredients'] and not r['has_error'])
    wet_total = sum(1 for r in results if r['is_wet'] and not r['has_error'])
    dry_with_ingr = sum(1 for r in results if not r['is_wet'] and r['has_ingredients'] and not r['has_error'])
    dry_total = sum(1 for r in results if not r['is_wet'] and not r['has_error'])
    
    if wet_total > 0:
        print(f"\nWet/Canned Food:")
        print(f"  With ingredients: {wet_with_ingr}/{wet_total} ({wet_with_ingr/wet_total*100:.1f}%)")
    
    if dry_total > 0:
        print(f"\nDry Food:")
        print(f"  With ingredients: {dry_with_ingr}/{dry_total} ({dry_with_ingr/dry_total*100:.1f}%)")

print(f"\nOverall:")
print(f"  Ingredients: {with_ingredients}/50 ({with_ingredients/50*100:.1f}%)")
print(f"  Nutrition: {with_nutrition}/50 ({with_nutrition/50*100:.1f}%)")

# List products still missing ingredients
missing_ingredients = [r for r in results if not r['has_ingredients'] and not r['has_error']]
if missing_ingredients:
    print(f"\n⚠️ {len(missing_ingredients)} products still missing ingredients:")
    for r in missing_ingredients[:10]:
        type_tag = "[WET]" if r['is_wet'] else "[DRY]"
        print(f"  {type_tag} {r['brand']}: {r['name'][:40]}")
    if len(missing_ingredients) > 10:
        print(f"  ... and {len(missing_ingredients)-10} more")

# Decision
print("\n" + "-"*60)
print("💡 ACCURACY ASSESSMENT:")

if successful > 0:
    accuracy = with_ingredients / successful * 100
    if accuracy >= 80:
        print(f"  ✅ EXCELLENT! {accuracy:.1f}% accuracy - READY FOR AUTOMATION")
        print("  → The improved patterns are working very well!")
    elif accuracy >= 60:
        print(f"  ✅ GOOD! {accuracy:.1f}% accuracy")
        print("  → Significant improvement, ready for deployment")
    elif accuracy >= 40:
        print(f"  ⚠️ MODERATE: {accuracy:.1f}% accuracy")
        print("  → Better but may need more pattern refinement")
    else:
        print(f"  ❌ NEEDS WORK: {accuracy:.1f}% accuracy")
        print("  → Patterns need further improvement")

# Save results
with open(f'data/test_50_results_{timestamp}.json', 'w') as f:
    json.dump({
        'timestamp': timestamp,
        'session_id': session_id,
        'total': 50,
        'successful': successful,
        'with_ingredients': with_ingredients,
        'with_nutrition': with_nutrition,
        'wet_food_count': wet_food_count,
        'dry_food_count': dry_food_count,
        'accuracy': with_ingredients / successful * 100 if successful > 0 else 0,
        'results': results
    }, f, indent=2)

print(f"\n💾 Results saved to data/test_50_results_{timestamp}.json")
print(f"📁 Scraped files in: gs://{GCS_BUCKET}/{gcs_folder}/")