#!/usr/bin/env python3
"""
Check what data is being extracted from scraped files
"""

import json
from google.cloud import storage
from dotenv import load_dotenv
import os

load_dotenv()
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

def check_extraction_stats():
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    
    # Check a recent folder
    folder = "scraped/zooplus/20250912_220318_es4"
    
    print("📊 CHECKING DATA EXTRACTION FROM SCRAPED FILES")
    print("=" * 50)
    print(f"Folder: {folder}\n")
    
    blobs = bucket.list_blobs(prefix=folder + "/")
    files_checked = 0
    with_ingredients = 0
    with_nutrition = 0
    nutrition_fields_count = {}
    
    for blob in blobs:
        if blob.name.endswith('.json'):
            files_checked += 1
            content = blob.download_as_text()
            data = json.loads(content)
            
            # Check ingredients
            if 'ingredients_raw' in data and data['ingredients_raw']:
                with_ingredients += 1
            
            # Check nutrition
            if 'nutrition' in data and data['nutrition']:
                with_nutrition += 1
                for field in data['nutrition'].keys():
                    nutrition_fields_count[field] = nutrition_fields_count.get(field, 0) + 1
            
            if files_checked <= 3:  # Show first 3 files
                print(f"File: {os.path.basename(blob.name)}")
                print(f"  Ingredients: {'Yes' if 'ingredients_raw' in data and data['ingredients_raw'] else 'No'}")
                if 'nutrition' in data:
                    print(f"  Nutrition: {list(data['nutrition'].keys())}")
                else:
                    print(f"  Nutrition: None")
                print()
    
    print(f"\n📈 EXTRACTION STATISTICS ({files_checked} files):")
    print(f"  With ingredients: {with_ingredients} ({with_ingredients/files_checked*100:.1f}%)")
    print(f"  With nutrition: {with_nutrition} ({with_nutrition/files_checked*100:.1f}%)")
    
    if nutrition_fields_count:
        print(f"\n🍖 NUTRITION FIELDS EXTRACTED:")
        for field, count in sorted(nutrition_fields_count.items()):
            print(f"  {field}: {count} files ({count/files_checked*100:.1f}%)")

if __name__ == "__main__":
    check_extraction_stats()