#!/usr/bin/env python3
"""
Retry scraping for PENDING products with working URLs
Focus on AADF and Zooplus products that previously failed
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()

# Initialize Supabase
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def analyze_retry_opportunities():
    """Analyze which PENDING products should be retried"""

    print("=== RETRY SCRAPING OPPORTUNITY ANALYSIS ===")
    print(f"Timestamp: {datetime.now()}")
    print()

    # Get all PENDING products with URLs
    print("Fetching PENDING products with URLs...")

    # Handle pagination
    all_pending = []
    batch_size = 1000
    offset = 0

    while True:
        batch = supabase.table('foods_published_preview').select(
            'product_key, brand, brand_slug, product_name, product_url, source, image_url, ingredients_tokens, protein_percent, fat_percent, kcal_per_100g'
        ).eq('allowlist_status', 'PENDING').range(offset, offset + batch_size - 1).execute()

        all_pending.extend(batch.data)

        if len(batch.data) < batch_size:
            break
        offset += batch_size

    print(f"Total PENDING products: {len(all_pending)}")

    # Filter for products with URLs
    products_with_urls = [p for p in all_pending if p.get('product_url')]
    print(f"PENDING products with URLs: {len(products_with_urls)}")
    print()

    # Categorize by source and missing data
    retry_categories = {
        'aadf_missing_nutrition': [],
        'aadf_missing_ingredients': [],
        'zooplus_missing_images': [],
        'zooplus_missing_ingredients': [],
        'zooplus_missing_all': []
    }

    for product in products_with_urls:
        source = product.get('source', '')
        has_image = bool(product.get('image_url'))
        has_ingredients = bool(product.get('ingredients_tokens'))
        has_nutrition = bool(product.get('protein_percent') or product.get('fat_percent') or product.get('kcal_per_100g'))

        if source == 'allaboutdogfood':
            if not has_nutrition:
                retry_categories['aadf_missing_nutrition'].append(product)
            if not has_ingredients:
                retry_categories['aadf_missing_ingredients'].append(product)

        elif source == 'zooplus_csv_import':
            if not has_image and not has_ingredients and not has_nutrition:
                retry_categories['zooplus_missing_all'].append(product)
            elif not has_image:
                retry_categories['zooplus_missing_images'].append(product)
            elif not has_ingredients:
                retry_categories['zooplus_missing_ingredients'].append(product)

    # Print analysis
    print("📊 RETRY OPPORTUNITIES BY CATEGORY:")
    print("=" * 60)

    total_retry = 0

    for category, products in retry_categories.items():
        if products:
            print(f"\n{category.upper().replace('_', ' ')}:")
            print(f"  Count: {len(products)} products")
            print(f"  Sample URLs (first 3):")
            for i, p in enumerate(products[:3]):
                print(f"    {i+1}. {p['product_name'][:50]}")
                print(f"       {p['product_url']}")
            total_retry += len(products)

    print("\n" + "=" * 60)
    print(f"TOTAL RETRY CANDIDATES: {total_retry} products")
    print()

    # Save retry lists to files
    print("Saving retry lists...")

    # AADF retry list
    aadf_retry = retry_categories['aadf_missing_nutrition'] + retry_categories['aadf_missing_ingredients']
    aadf_retry = list({p['product_key']: p for p in aadf_retry}.values())  # Remove duplicates

    if aadf_retry:
        with open('retry_aadf_pending.json', 'w') as f:
            import json
            json.dump(aadf_retry, f, indent=2)
        print(f"✅ Saved {len(aadf_retry)} AADF products to retry_aadf_pending.json")

    # Zooplus retry list
    zooplus_retry = (retry_categories['zooplus_missing_all'] +
                     retry_categories['zooplus_missing_images'] +
                     retry_categories['zooplus_missing_ingredients'])
    zooplus_retry = list({p['product_key']: p for p in zooplus_retry}.values())  # Remove duplicates

    if zooplus_retry:
        with open('retry_zooplus_pending.json', 'w') as f:
            import json
            json.dump(zooplus_retry, f, indent=2)
        print(f"✅ Saved {len(zooplus_retry)} Zooplus products to retry_zooplus_pending.json")

    print()
    print("🎯 RECOMMENDED ACTIONS:")
    print("1. Run AADF nutrition scraper on retry_aadf_pending.json")
    print("2. Run Zooplus Pattern 8 scraper on retry_zooplus_pending.json")
    print("3. Monitor success rates and adjust patterns if needed")
    print("4. Update database with newly scraped data")

    return {
        'aadf_retry': aadf_retry,
        'zooplus_retry': zooplus_retry
    }

if __name__ == '__main__':
    analyze_retry_opportunities()