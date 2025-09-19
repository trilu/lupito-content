#!/usr/bin/env python3
"""
Process PetFoodExpert scraped data from GCS to database
"""

import os
import json
from datetime import datetime
from google.cloud import storage
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize services
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/sergiubiris/Desktop/lupito-content/secrets/gcp-sa.json'
storage_client = storage.Client()
bucket = storage_client.bucket('lupito-content-raw-eu')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def process_petfoodexpert_data():
    """Process all PetFoodExpert data from GCS to database"""
    
    print("📊 PROCESSING PETFOODEXPERT DATA TO DATABASE")
    print("=" * 60)
    
    # Get all PetFoodExpert files
    prefix = 'scraped/petfoodexpert/'
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    print(f"Found {len(blobs)} files to process")
    
    # Statistics
    stats = {
        'total_files': len(blobs),
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'skipped': 0,
        'with_ingredients': 0,
        'with_nutrition': 0
    }
    
    # Process each file
    for i, blob in enumerate(blobs, 1):
        if i % 100 == 0:
            print(f"Processing {i}/{len(blobs)} ({i/len(blobs)*100:.1f}%)...")
        
        try:
            # Download and parse JSON
            content = blob.download_as_text()
            data = json.loads(content)
            
            # Skip if error or no ingredients
            if 'error' in data:
                stats['skipped'] += 1
                continue
            
            if 'ingredients_raw' not in data and 'nutrition' not in data:
                stats['skipped'] += 1
                continue
            
            # Prepare update data
            update_data = {}
            
            # Add ingredients if present
            if 'ingredients_raw' in data:
                update_data['ingredients_raw'] = data['ingredients_raw'][:3000]  # Limit to 3000 chars
                stats['with_ingredients'] += 1
            
            # Add nutrition if present
            if 'nutrition' in data:
                nutrition = data['nutrition']
                if 'protein_percent' in nutrition:
                    update_data['protein_percent'] = nutrition['protein_percent']
                if 'fat_percent' in nutrition:
                    update_data['fat_percent'] = nutrition['fat_percent']
                if 'fiber_percent' in nutrition:
                    update_data['fiber_percent'] = nutrition['fiber_percent']
                if 'ash_percent' in nutrition:
                    update_data['ash_percent'] = nutrition['ash_percent']
                if 'moisture_percent' in nutrition:
                    update_data['moisture_percent'] = nutrition['moisture_percent']
                stats['with_nutrition'] += 1
            
            # Update database
            if update_data and 'product_key' in data:
                try:
                    # Update the product in database
                    response = supabase.table('foods_canonical')\
                        .update(update_data)\
                        .eq('product_key', data['product_key'])\
                        .execute()
                    
                    if response.data:
                        stats['updated'] += 1
                    else:
                        print(f"  Warning: No rows updated for {data['product_key']}")
                        
                except Exception as e:
                    print(f"  Error updating {data.get('product_key', 'unknown')}: {str(e)[:100]}")
                    stats['errors'] += 1
            
            stats['processed'] += 1
            
        except json.JSONDecodeError:
            print(f"  Error: Invalid JSON in {blob.name}")
            stats['errors'] += 1
        except Exception as e:
            print(f"  Error processing {blob.name}: {str(e)[:100]}")
            stats['errors'] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total files: {stats['total_files']}")
    print(f"Processed: {stats['processed']}")
    print(f"Updated in DB: {stats['updated']}")
    print(f"With ingredients: {stats['with_ingredients']}")
    print(f"With nutrition: {stats['with_nutrition']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    
    success_rate = (stats['updated'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    # Check new coverage
    print("\n📈 CHECKING NEW DATABASE COVERAGE:")
    print("-" * 40)
    
    # Total products
    total_result = supabase.table('foods_canonical')\
        .select('count', count='exact')\
        .execute()
    total_count = total_result.count
    
    # Products with ingredients
    with_ingredients = supabase.table('foods_canonical')\
        .select('count', count='exact')\
        .not_.is_('ingredients_raw', 'null')\
        .execute()
    ingredients_count = with_ingredients.count
    
    # PetFoodExpert specific
    petfood_total = supabase.table('foods_canonical')\
        .select('count', count='exact')\
        .ilike('product_url', '%petfoodexpert%')\
        .execute()
    petfood_count = petfood_total.count
    
    petfood_with_ingredients = supabase.table('foods_canonical')\
        .select('count', count='exact')\
        .ilike('product_url', '%petfoodexpert%')\
        .not_.is_('ingredients_raw', 'null')\
        .execute()
    petfood_ingredients_count = petfood_with_ingredients.count
    
    # Calculate percentages
    overall_coverage = (ingredients_count / total_count * 100) if total_count > 0 else 0
    petfood_coverage = (petfood_ingredients_count / petfood_count * 100) if petfood_count > 0 else 0
    
    print(f"Overall database:")
    print(f"  Total products: {total_count:,}")
    print(f"  With ingredients: {ingredients_count:,} ({overall_coverage:.1f}%)")
    
    print(f"\nPetFoodExpert:")
    print(f"  Total products: {petfood_count:,}")
    print(f"  With ingredients: {petfood_ingredients_count:,} ({petfood_coverage:.1f}%)")
    
    print("\n✅ Processing complete!")
    return stats

if __name__ == "__main__":
    process_petfoodexpert_data()