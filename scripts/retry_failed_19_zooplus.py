#!/usr/bin/env python3
"""
Retry the 19 failed Zooplus products one by one
"""

import os
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from google.cloud import storage
from supabase import create_client

load_dotenv()

# Configuration
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET", "lupito-content-raw-eu")

# Initialize clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET)

# The 19 failed products
FAILED_PRODUCTS = [
    {
        "name": "Terra Canis Essential 8+ 6 x 780g",
        "key": "terracanis|terra_canis_essential_8_6_x_780g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/terracanis_menu/1948338?activeVariant=1948338.1"
    },
    {
        "name": "Terra Canis Classic 12 x 200g",
        "key": "terracanis|terra_canis_classic_12_x_200g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/terracanis_menu/963023?activeVariant=963023.1"
    },
    {
        "name": "Purizon Adult 6 x 300g",
        "key": "purizonwetdogfood|purizon_adult_6_x_300g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/purizon_wet_dog_food/adult/1549511?activeVariant=1549511.5"
    },
    {
        "name": "WOW Adult 6 x 400 g",
        "key": "wow|wow_adult_6_x_400_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wow/1947703?activeVariant=1947703.3"
    },
    {
        "name": "WOW Adult 6 x 800 g",
        "key": "wow|wow_adult_6_x_800_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wow/1947704?activeVariant=1947704.4"
    },
    {
        "name": "WOW Junior 6 x 400 g",
        "key": "wow|wow_junior_6_x_400_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wow/1947745?activeVariant=1947745.0"
    },
    {
        "name": "DIBO Exclusive 6 x 800g",
        "key": "dibo|dibo_exclusive_6_x_800g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/dibo/2104305?activeVariant=2104305.0"
    },
    {
        "name": "Saver Pack Josera Meatlovers Pure 12 x 800g",
        "key": "joserawet|saver_pack_josera_meatlovers_pure_12_x_800g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/josera_wet/1319842?activeVariant=1319842.0"
    },
    {
        "name": "Terra Canis Classic Saver Pack 12 x 400g",
        "key": "terracanis|terra_canis_classic_saver_pack_12_x_400g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949802?activeVariant=1949802.0"
    },
    {
        "name": "Terra Canis Alimentum Veterinarium Diabetic Diet 6 x 400 g",
        "key": "terracanis|terra_canis_alimentum_veterinarium_diabetic_diet_6_x_400_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949851?activeVariant=1949851.0"
    },
    {
        "name": "Terra Canis Classic 6 x 400g",
        "key": "terracanis|terra_canis_classic_6_x_400g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949852?activeVariant=1949852.0"
    },
    {
        "name": "Terra Canis Alimentum Veterinarium Intestinal 6 x 400 g",
        "key": "terracanis|terra_canis_alimentum_veterinarium_intestinal_6_x_400_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949855?activeVariant=1949855.0"
    },
    {
        "name": "Saver Pack Terra Canis Alimentum Veterinarium Intestinal 12 x 400 g",
        "key": "terracanis|saver_pack_terra_canis_alimentum_veterinarium_intestinal_12_x_400_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949856?activeVariant=1949856.0"
    },
    {
        "name": "Terra Canis Mini 18 x 100 g",
        "key": "terracanis|terra_canis_mini_18_x_100_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949857?activeVariant=1949857.1"
    },
    {
        "name": "Terra Canis Alimentum Veterinarium Low Mineral Diet Saver Pack 12 x 400g",
        "key": "terracanis|terra_canis_alimentum_veterinarium_low_mineral_diet_saver_pack_12_x_400g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949862?activeVariant=1949862.0"
    },
    {
        "name": "Saver Pack Terra Canis 12 x 800 g",
        "key": "terracanis|saver_pack_terra_canis_12_x_800_g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/1949863?activeVariant=1949863.0"
    },
    {
        "name": "Terra Canis Hypoallergenic 6 x 800g",
        "key": "terracanis|terra_canis_hypoallergenic_6_x_800g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/hypo_menus/925292?activeVariant=925292.1"
    },
    {
        "name": "Terra Canis Hypoallergenic 12 x 800g",
        "key": "terracanis|terra_canis_hypoallergenic_12_x_800g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/hypo_menus/925293?activeVariant=925293.0"
    },
    {
        "name": "Terra Canis Saver Pack 12 x 800g",
        "key": "terracanis|terra_canis_saver_pack_12_x_800g|wet",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/terra_canis/saver_packs/330395?activeVariant=330395.9"
    }
]

def scrape_with_retry(url, attempt=1):
    """Scrape with retry logic"""
    print(f"  Attempt {attempt}...")

    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'gb',
        'wait': '5000',  # Increased wait time
        'return_page_source': 'true'
    }

    # Try different country codes if first attempt fails
    if attempt == 2:
        params['country_code'] = 'de'
    elif attempt == 3:
        params['country_code'] = 'us'

    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=90
        )

        if response.status_code == 200:
            return response.text
        else:
            print(f"    HTTP {response.status_code}: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"    Exception: {str(e)[:100]}")
        return None

def extract_data(html, product_key):
    """Extract data using Pattern 8 and other patterns"""

    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text('\n', strip=True)

    result = {
        'product_key': product_key,
        'scraped_at': datetime.now().isoformat(),
        'session_id': 'retry_19_manual'
    }

    # Extract image
    img_selectors = [
        'img.ProductImage__image',
        'div.ProductImage img',
        'picture.ProductImage__picture img',
        'div.swiper-slide img',
        'img[alt*="product"]'
    ]

    for selector in img_selectors:
        img = soup.select_one(selector)
        if img and img.get('src'):
            result['image_url'] = img['src']
            break

    # Pattern 8 for ingredients
    pattern_8 = r'Go to analytical constituents\s*\n(.*?)(?:Analytical constituents|$)'
    match = re.search(pattern_8, page_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)

    if match:
        result['pattern_8_matched'] = True
        captured = match.group(1).strip()

        # Extract ingredients from captured content
        inner_pattern = r'Ingredients[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)'
        inner_match = re.search(inner_pattern, captured, re.IGNORECASE | re.MULTILINE)

        if inner_match:
            ingredients = inner_match.group(1).strip()
            if len(ingredients) > 20:
                result['ingredients_raw'] = ingredients[:3000]

    # Fallback patterns
    if 'ingredients_raw' not in result:
        patterns = [
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)',
            r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                ingredients = match.group(1).strip()
                if len(ingredients) > 20:
                    result['ingredients_raw'] = ingredients[:3000]
                    break

    # Extract nutrition
    nutrition_patterns = [
        (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein_percent'),
        (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat_percent'),
        (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber_percent'),
    ]

    for pattern, key in nutrition_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            result[key] = float(match.group(1))

    return result

def main():
    print("="*60)
    print("RETRYING 19 FAILED ZOOPLUS PRODUCTS")
    print("="*60)
    print(f"Time: {datetime.now()}")
    print()

    session_id = datetime.now().strftime('%Y%m%d_%H%M%S_retry_19')
    gcs_folder = f"scraped/zooplus_retry/{session_id}"

    stats = {
        'total': 0,
        'success': 0,
        'with_images': 0,
        'with_ingredients': 0,
        'with_nutrition': 0
    }

    for i, product in enumerate(FAILED_PRODUCTS, 1):
        print(f"\n[{i}/19] {product['name']}")
        print(f"  URL: {product['url'][:80]}...")

        stats['total'] += 1

        # Try up to 3 times
        html = None
        for attempt in range(1, 4):
            html = scrape_with_retry(product['url'], attempt)
            if html:
                break
            if attempt < 3:
                print(f"  Retrying in 10 seconds...")
                time.sleep(10)

        if html:
            print(f"  ✅ Scraped ({len(html)} bytes)")

            # Extract data
            data = extract_data(html, product['key'])

            # Save to GCS
            try:
                safe_key = product['key'].replace('|', '_').replace('/', '_')
                filename = f"{gcs_folder}/{safe_key}.json"

                blob = bucket.blob(filename)
                blob.upload_from_string(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    content_type='application/json'
                )
                print(f"  ✅ Saved to GCS")
            except Exception as e:
                print(f"  ❌ GCS error: {str(e)[:100]}")

            # Update database (with truncation for constraint)
            try:
                update_data = {}

                if 'image_url' in data:
                    update_data['image_url'] = data['image_url']
                    stats['with_images'] += 1
                    print(f"  📸 Image found")

                if 'ingredients_raw' in data:
                    # Truncate to 3000 chars to avoid constraint violation
                    update_data['ingredients_tokens'] = data['ingredients_raw'][:3000]
                    update_data['ingredients_source'] = 'zooplus_retry_19'
                    stats['with_ingredients'] += 1
                    print(f"  🥩 Ingredients found ({len(data['ingredients_raw'])} chars)")

                if 'protein_percent' in data:
                    update_data['protein_percent'] = data['protein_percent']
                    update_data['fat_percent'] = data.get('fat_percent')
                    update_data['fiber_percent'] = data.get('fiber_percent')
                    stats['with_nutrition'] += 1
                    print(f"  📊 Nutrition found")

                if update_data:
                    supabase.table('foods_canonical').update(update_data).eq(
                        'product_key', product['key']
                    ).execute()
                    print(f"  ✅ Updated database")

            except Exception as e:
                print(f"  ⚠️ DB update error: {str(e)[:100]}")

            stats['success'] += 1
        else:
            print(f"  ❌ Failed after 3 attempts")

        # Delay between products
        if i < 19:
            delay = 15
            print(f"  Waiting {delay} seconds...")
            time.sleep(delay)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total: {stats['total']}")
    print(f"Success: {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
    print(f"With images: {stats['with_images']}")
    print(f"With ingredients: {stats['with_ingredients']}")
    print(f"With nutrition: {stats['with_nutrition']}")
    print(f"GCS folder: gs://{GCS_BUCKET}/{gcs_folder}/")

if __name__ == '__main__':
    main()