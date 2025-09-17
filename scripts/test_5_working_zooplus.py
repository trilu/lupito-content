#!/usr/bin/env python3
"""
Test 5 manually verified working Zooplus URLs
Using correct ScrapingBee setup from existing scripts
"""

import os
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests

load_dotenv()

# Use the correct env variable name
SCRAPINGBEE_API_KEY = os.getenv('SCRAPING_BEE')

# 5 manually tested working URLs
TEST_URLS = [
    {
        "name": "Wolf of Wilderness Senior",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/wolf_of_wilderness_senior/651160?activeVariant=651160.0"
    },
    {
        "name": "Wolf of Wilderness Junior",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/wolf_of_wilderness/junior/2178870?activeVariant=2178870.2"
    },
    {
        "name": "Rocco Diet Care",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/rocco/rocco_diet_care/2152397?activeVariant=2152397.0"
    },
    {
        "name": "Dogs N Tiger Puppy",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/dogs_n_tiger/puppy/1966735?activeVariant=1966735.0"
    },
    {
        "name": "Natures Variety",
        "url": "https://www.zooplus.com/shop/dogs/canned_dog_food/naturesvariety/1584332?activeVariant=1584332.0"
    }
]

def scrape_with_scrapingbee(url):
    """Scrape using ScrapingBee with proven parameters"""

    print(f"  Scraping: {url[:80]}...")

    # Use same parameters as orchestrated scraper
    params = {
        'api_key': SCRAPINGBEE_API_KEY,
        'url': url,
        'render_js': 'true',
        'premium_proxy': 'true',
        'stealth_proxy': 'true',
        'country_code': 'gb',
        'wait': '3000',
        'return_page_source': 'true'
    }

    try:
        response = requests.get(
            'https://app.scrapingbee.com/api/v1/',
            params=params,
            timeout=60
        )

        print(f"  Response status: {response.status_code}")

        if response.status_code == 200:
            return response.text
        else:
            print(f"  Error content: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"  Exception: {str(e)}")
        return None

def extract_data(html):
    """Extract image, ingredients, and nutrition using Pattern 8 and others"""

    soup = BeautifulSoup(html, 'html.parser')
    page_text = soup.get_text('\n', strip=True)

    result = {
        'image_found': False,
        'ingredients_found': False,
        'nutrition_found': False,
        'pattern_8_matched': False
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
            result['image_found'] = True
            result['image_url'] = img['src'][:100] + '...'
            break

    # Try Pattern 8 for ingredients
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
                result['ingredients_found'] = True
                result['ingredients_preview'] = ingredients[:100] + '...'

    # Also try other ingredient patterns
    if not result['ingredients_found']:
        patterns = [
            r'(?:Composition|Ingredients)[:\s]*\n?([^\n]{20,}?)(?:\n(?:Analytical|Additives)|$)',
            r'Ingredients:\s*\n((?:Duck|Chicken|Meat|Lamb|Beef|Turkey|Salmon|Fish)[^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                ingredients = match.group(1).strip()
                if len(ingredients) > 20:
                    result['ingredients_found'] = True
                    result['ingredients_preview'] = ingredients[:100] + '...'
                    result['other_pattern_matched'] = True
                    break

    # Extract nutrition
    nutrition_patterns = [
        (r'(?:Crude\s+)?Protein[:\s]+(\d+(?:\.\d+)?)\s*%', 'protein'),
        (r'(?:Crude\s+)?(?:Fat|Oils)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fat'),
        (r'(?:Crude\s+)?Fib(?:re|er)[:\s]+(\d+(?:\.\d+)?)\s*%', 'fiber'),
    ]

    nutrition = {}
    for pattern, key in nutrition_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            nutrition[key] = float(match.group(1))

    if nutrition:
        result['nutrition_found'] = True
        result['nutrition'] = nutrition

    return result

def main():
    print("=" * 60)
    print("TESTING 5 WORKING ZOOPLUS URLS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"API Key: {'Set' if SCRAPINGBEE_API_KEY else 'MISSING!'}")
    print()

    if not SCRAPINGBEE_API_KEY:
        print("ERROR: SCRAPING_BEE environment variable not found!")
        return

    results = []
    stats = {
        'success': 0,
        'image': 0,
        'ingredients': 0,
        'nutrition': 0,
        'pattern_8': 0
    }

    for i, test in enumerate(TEST_URLS, 1):
        print(f"\n[{i}/5] Testing: {test['name']}")

        html = scrape_with_scrapingbee(test['url'])

        if html:
            print(f"  ✅ Successfully scraped ({len(html)} bytes)")

            data = extract_data(html)
            results.append({
                'name': test['name'],
                'url': test['url'],
                **data
            })

            stats['success'] += 1
            if data['image_found']:
                stats['image'] += 1
                print(f"  ✅ Image found")
            else:
                print(f"  ❌ No image")

            if data['ingredients_found']:
                stats['ingredients'] += 1
                print(f"  ✅ Ingredients found")
                if data.get('pattern_8_matched'):
                    stats['pattern_8'] += 1
                    print(f"     (via Pattern 8)")
            else:
                print(f"  ❌ No ingredients")

            if data['nutrition_found']:
                stats['nutrition'] += 1
                print(f"  ✅ Nutrition found: {data['nutrition']}")
            else:
                print(f"  ❌ No nutrition")
        else:
            print(f"  ❌ Failed to scrape")
            results.append({
                'name': test['name'],
                'url': test['url'],
                'error': 'Failed to scrape'
            })

        # Wait between requests
        if i < 5:
            print(f"  Waiting 5 seconds...")
            time.sleep(5)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Successful scrapes: {stats['success']}/5")
    print(f"Images found: {stats['image']}/5")
    print(f"Ingredients found: {stats['ingredients']}/5")
    print(f"  - Via Pattern 8: {stats['pattern_8']}")
    print(f"Nutrition found: {stats['nutrition']}/5")

    # Save results
    output_file = f"test_5_zooplus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
            'results': results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    if stats['success'] >= 3:
        print("\n✅ SUCCESS: ScrapingBee works with these URLs!")
        print("The issue is with the CSV import URLs being stale/broken.")
    else:
        print("\n⚠️ ISSUES: Even these URLs have problems.")

if __name__ == '__main__':
    main()