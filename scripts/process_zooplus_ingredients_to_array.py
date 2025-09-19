#!/usr/bin/env python3
"""
Process Zooplus ingredients from GCS and convert to array format for database
"""

import os
import json
import re
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

def parse_ingredients_to_array(ingredients_text):
    """
    Parse ingredients text into an array of individual ingredients
    """
    if not ingredients_text:
        return []

    # Clean up the text
    text = ingredients_text.strip()

    # Remove common prefixes
    text = re.sub(r'^(Composition|Ingredients|Analytical constituents)[:\s]*', '', text, flags=re.IGNORECASE)

    # Remove percentage in parentheses but keep the ingredient
    # e.g., "chicken (26%)" -> "chicken"
    text = re.sub(r'\s*\([^)]*%[^)]*\)', '', text)

    # Split by comma, semicolon, or pattern like "and" at end
    # But be careful with ingredients like "meat and animal derivatives"
    ingredients = []

    # First try to split by comma
    parts = text.split(',')

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Handle cases like "vitamins and minerals" as single ingredient
        # But split "chicken and rice" into two
        if ' and ' in part.lower():
            # Check if it's a common compound ingredient
            compound_patterns = [
                'vitamins and minerals',
                'meat and animal derivatives',
                'oils and fats',
                'fish and fish derivatives',
                'cereals and cereal derivatives',
                'vegetables and vegetable derivatives',
                'fruits and fruit derivatives',
                'herbs and botanicals'
            ]

            is_compound = False
            for pattern in compound_patterns:
                if pattern in part.lower():
                    is_compound = True
                    break

            if not is_compound and not 'derivatives' in part.lower():
                # Split it
                sub_parts = part.split(' and ')
                for sp in sub_parts:
                    sp = sp.strip()
                    if sp and len(sp) > 2:  # Avoid single letters
                        ingredients.append(sp)
            else:
                # Keep as single ingredient
                ingredients.append(part)
        else:
            ingredients.append(part)

    # Clean up each ingredient
    cleaned = []
    for ing in ingredients:
        # Remove leading/trailing whitespace
        ing = ing.strip()

        # Remove trailing periods
        ing = ing.rstrip('.')

        # Skip if too short or looks like garbage
        if len(ing) < 3:
            continue

        # Skip if it's just numbers or special chars
        if not re.search(r'[a-zA-Z]', ing):
            continue

        # Lowercase first letter unless it's an acronym or proper noun
        if ing and not ing.isupper() and ing[0].isupper() and not re.match(r'^[A-Z]{2,}', ing):
            ing = ing[0].lower() + ing[1:]

        cleaned.append(ing)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for ing in cleaned:
        if ing.lower() not in seen:
            seen.add(ing.lower())
            unique.append(ing)

    return unique

def process_gcs_folder(folder_path):
    """Process all JSON files in a GCS folder"""

    stats = {
        'total': 0,
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'with_ingredients': 0,
        'parsed_ingredients': 0
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

                # Process ingredients
                if 'ingredients_raw' in data and data['ingredients_raw']:
                    stats['with_ingredients'] += 1

                    # Parse ingredients to array
                    ingredients_array = parse_ingredients_to_array(data['ingredients_raw'])

                    if ingredients_array:
                        stats['parsed_ingredients'] += 1

                        # Update database with array format
                        try:
                            update_data = {
                                'ingredients_tokens': ingredients_array,
                                'ingredients_source': 'site'
                            }

                            # Update in database
                            result = supabase.table('foods_canonical').update(update_data).eq(
                                'product_key', product_key
                            ).execute()

                            if result.data:
                                stats['updated'] += 1
                                print(f"  ✅ Updated: {product_key} ({len(ingredients_array)} ingredients)")
                            else:
                                print(f"  ⚠️ No update for: {product_key}")

                        except Exception as e:
                            print(f"  ❌ DB error for {product_key}: {str(e)[:100]}")
                            stats['errors'] += 1
                    else:
                        print(f"  ⚠️ Could not parse ingredients for: {product_key}")

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
    print("PROCESSING ZOOPLUS INGREDIENTS TO ARRAY FORMAT")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print()

    # Test parsing first
    print("Testing ingredient parsing...")
    test_cases = [
        "Fresh salmon 26%, fish meal, peas, sweet potato, beet pulp, fish oil, vitamins and minerals",
        "Chicken (fresh 25%), turkey meal, rice, barley, chicken fat, dried beet pulp",
        "Meat and animal derivatives (4% beef), cereals, oils and fats, vegetable protein extracts"
    ]

    for test in test_cases:
        parsed = parse_ingredients_to_array(test)
        print(f"\nOriginal: {test[:60]}...")
        print(f"Parsed ({len(parsed)}): {parsed[:5]}")

    print("\n" + "="*60)
    print("PROCESSING GCS FILES")
    print("="*60)

    # Process both folders
    folders = [
        "scraped/zooplus_retry/20250916_222711_full_208/",  # Main batch
        "scraped/zooplus_retry/20250917_111845_retry_19/"   # Retry batch
    ]

    total_stats = {
        'total': 0,
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'with_ingredients': 0,
        'parsed_ingredients': 0
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
        print(f"  With ingredients: {folder_stats['with_ingredients']}")
        print(f"  Successfully parsed: {folder_stats['parsed_ingredients']}")
        print(f"  Updated: {folder_stats['updated']}")
        print(f"  Errors: {folder_stats['errors']}")

    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total files: {total_stats['total']}")
    print(f"Files with ingredients: {total_stats['with_ingredients']}")
    print(f"Successfully parsed: {total_stats['parsed_ingredients']}")
    print(f"Database updated: {total_stats['updated']} ({total_stats['updated']/max(total_stats['total'],1)*100:.1f}%)")
    print(f"Errors: {total_stats['errors']}")

    # Check final database status
    print("\n" + "="*60)
    print("DATABASE STATUS CHECK")
    print("="*60)

    response = supabase.table('foods_canonical').select(
        'product_key'
    ).eq('source', 'zooplus_csv_import')\
    .not_.is_('ingredients_tokens', 'null')\
    .execute()

    with_ingredients = len(response.data) if response.data else 0

    response = supabase.table('foods_canonical').select(
        'product_key'
    ).eq('source', 'zooplus_csv_import')\
    .execute()

    total_zooplus = len(response.data) if response.data else 0

    print(f"Total Zooplus products: {total_zooplus}")
    print(f"With ingredients: {with_ingredients} ({with_ingredients/max(total_zooplus,1)*100:.1f}%)")

if __name__ == '__main__':
    main()