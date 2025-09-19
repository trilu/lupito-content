#!/usr/bin/env python3
"""
Analyze test results from improved scraper
"""

import json
import subprocess

# Get list of files
result = subprocess.run(
    ['gsutil', 'ls', 'gs://lupito-content-raw-eu/scraped/zooplus/test_improved_20250913_142643/*.json'],
    capture_output=True, text=True
)

files = result.stdout.strip().split('\n') if result.stdout else []

print(f"📊 ANALYZING {len(files)} SCRAPED FILES")
print("="*60)

with_ingredients = 0
with_nutrition = 0
errors = 0

for file_path in files:
    # Download file content
    result = subprocess.run(
        ['gsutil', 'cat', file_path],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            
            has_ingredients = 'ingredients_raw' in data
            has_nutrition = 'nutrition' in data
            
            if has_ingredients:
                with_ingredients += 1
            if has_nutrition:
                with_nutrition += 1
            
            print(f"✓ {data.get('original_name', 'Unknown')[:40]:40} | Ingr: {'✅' if has_ingredients else '❌'} | Nutr: {'✅' if has_nutrition else '❌'}")
            
        except json.JSONDecodeError:
            errors += 1

print("\n" + "-"*60)
print("RESULTS:")
print(f"  Total files: {len(files)}")
print(f"  With ingredients: {with_ingredients}/{len(files)} ({with_ingredients/len(files)*100:.1f}%)")
print(f"  With nutrition: {with_nutrition}/{len(files)} ({with_nutrition/len(files)*100:.1f}%)")

if with_ingredients/len(files) >= 0.95:
    print("\n✅ EXCELLENT! >95% extraction rate - ready for full automation")
elif with_ingredients/len(files) >= 0.70:
    print("\n✅ GOOD! >70% extraction rate - significant improvement")
else:
    print(f"\n⚠️ MODERATE: {with_ingredients/len(files)*100:.1f}% extraction rate")