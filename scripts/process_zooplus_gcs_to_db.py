#!/usr/bin/env python3
"""
Process Zooplus scraped data from GCS to database
Handles the constraint issue by truncating ingredients_tokens to 3000 chars
"""

import os
import json
from datetime import datetime
from google.cloud import storage
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

def process_gcs_folder(folder_path):
    """Process all JSON files in a GCS folder"""

    stats = {
        'total': 0,
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'with_images': 0,
        'with_ingredients': 0,
        'with_nutrition': 0
    }

    print(f"Processing folder: {folder_path}")

    # List all JSON files in the folder
    blobs = bucket.list_blobs(prefix=folder_path)

    for blob in blobs:
        if blob.name.endswith('.json'):
            stats['total'] += 1

            try:
                # Download and parse JSON
                content = blob.download_as_text()
                data = json.loads(content)

                product_key = data.get('product_key')
                if not product_key:
                    print(f"  ⚠️ No product_key in {blob.name}")
                    stats['errors'] += 1
                    continue

                # Prepare update data
                update_data = {}

                # Image URL
                if 'image_url' in data and data['image_url']:
                    update_data['image_url'] = data['image_url']
                    stats['with_images'] += 1

                # Ingredients - TRUNCATE TO 3000 CHARS to avoid constraint
                if 'ingredients_raw' in data and data['ingredients_raw']:
                    # Truncate to 3000 characters maximum
                    ingredients = data['ingredients_raw'][:3000]
                    update_data['ingredients_tokens'] = ingredients
                    update_data['ingredients_source'] = 'site'  # Must be 'site' per database constraint
                    stats['with_ingredients'] += 1

                # Nutrition data
                if 'protein_percent' in data:
                    update_data['protein_percent'] = data['protein_percent']
                    stats['with_nutrition'] += 1
                if 'fat_percent' in data:
                    update_data['fat_percent'] = data['fat_percent']
                if 'fiber_percent' in data:
                    update_data['fiber_percent'] = data['fiber_percent']
                if 'ash_percent' in data:
                    update_data['ash_percent'] = data['ash_percent']
                if 'moisture_percent' in data:
                    update_data['moisture_percent'] = data['moisture_percent']

                # Update database if we have data
                if update_data:
                    try:
                        # First check if product exists
                        check = supabase.table('foods_canonical').select('product_key').eq(
                            'product_key', product_key
                        ).execute()

                        if check.data:
                            # Update existing product
                            result = supabase.table('foods_canonical').update(update_data).eq(
                                'product_key', product_key
                            ).execute()

                            if result.data:
                                stats['updated'] += 1
                                print(f"  ✅ Updated: {product_key}")
                            else:
                                print(f"  ⚠️ No update for: {product_key}")
                        else:
                            print(f"  ❌ Product not found: {product_key}")
                            stats['errors'] += 1

                    except Exception as e:
                        print(f"  ❌ DB error for {product_key}: {str(e)[:100]}")
                        stats['errors'] += 1

                stats['processed'] += 1

                # Progress indicator
                if stats['processed'] % 10 == 0:
                    print(f"  Progress: {stats['processed']}/{stats['total']}")

            except Exception as e:
                print(f"  ❌ Error processing {blob.name}: {str(e)[:100]}")
                stats['errors'] += 1

    return stats

def main():
    print("="*60)
    print("PROCESSING ZOOPLUS GCS DATA TO DATABASE")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print()

    # Process both folders
    folders = [
        "scraped/zooplus_retry/20250916_222711_full_208/",  # Main batch (189 files)
        "scraped/zooplus_retry/20250917_111845_retry_19/"   # Retry batch (19 files)
    ]

    total_stats = {
        'total': 0,
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'with_images': 0,
        'with_ingredients': 0,
        'with_nutrition': 0
    }

    for folder in folders:
        print(f"\n{'='*40}")
        print(f"Processing: {folder}")
        print('='*40)

        folder_stats = process_gcs_folder(folder)

        # Aggregate stats
        for key in total_stats:
            total_stats[key] += folder_stats[key]

        # Folder summary
        print(f"\nFolder Summary:")
        print(f"  Total files: {folder_stats['total']}")
        print(f"  Processed: {folder_stats['processed']}")
        print(f"  Updated: {folder_stats['updated']}")
        print(f"  Errors: {folder_stats['errors']}")

    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total files: {total_stats['total']}")
    print(f"Processed: {total_stats['processed']}")
    print(f"Successfully updated: {total_stats['updated']} ({total_stats['updated']/max(total_stats['total'],1)*100:.1f}%)")
    print(f"With images: {total_stats['with_images']}")
    print(f"With ingredients: {total_stats['with_ingredients']}")
    print(f"With nutrition: {total_stats['with_nutrition']}")
    print(f"Errors: {total_stats['errors']}")

    # Check final status in database
    print("\n" + "="*60)
    print("DATABASE STATUS CHECK")
    print("="*60)

    # Count Zooplus products with data
    response = supabase.table('foods_canonical').select(
        'product_key'
    ).eq('source', 'zooplus_csv_import')\
    .not_.is_('ingredients_tokens', 'null')\
    .execute()

    with_ingredients = len(response.data) if response.data else 0

    response = supabase.table('foods_canonical').select(
        'product_key'
    ).eq('source', 'zooplus_csv_import')\
    .not_.is_('image_url', 'null')\
    .execute()

    with_images = len(response.data) if response.data else 0

    response = supabase.table('foods_canonical').select(
        'product_key'
    ).eq('source', 'zooplus_csv_import')\
    .execute()

    total_zooplus = len(response.data) if response.data else 0

    print(f"Total Zooplus products: {total_zooplus}")
    print(f"With ingredients: {with_ingredients} ({with_ingredients/max(total_zooplus,1)*100:.1f}%)")
    print(f"With images: {with_images} ({with_images/max(total_zooplus,1)*100:.1f}%)")

    # Check PENDING status
    response = supabase.table('foods_published_preview').select(
        'count'
    ).eq('source', 'zooplus_csv_import')\
    .eq('allowlist_status', 'PENDING')\
    .execute()

    if response.data and response.data[0]:
        pending = response.data[0].get('count', 0)
        print(f"\nZooplus products still PENDING: {pending}")
        print(f"Ready for publication: {208 - pending}/208")

if __name__ == '__main__':
    main()